from rasa_sdk import Tracker
import json
import copy
import logging

from src.database.dao_user import DAOUser
from src.utils.records import *
from config import *

records_init = {
}
# reset_actions = [
#     "action_start",
#     "action_start_order"
# ]

# roll_back_entities = [
#     "action_reset_order"
# ]

# name_entities_roll_back = [
#     "name", "size", "amount", "order"
# ]

dao_user = DAOUser()


class Recorder:
    """
    record of conversation by sender_id
    """

    def __init__(self, sender_id) -> None:
        self.sender_id = sender_id
        self.pre_action = None
        self.cur_action = None
        self.cur_intent = None
        self.last_message = None
        self.custom_records = copy.deepcopy(records_init)
        self.slots_record = {}
        with open(PATH_CONFIG_USER_INFO, encoding='utf8') as file_user_info:
            self.user_info = json.load(file_user_info)
        with open(PATH_CONFIG_USER_PARAMS, "r") as file_slot:
            self.reader_config_slots = json.load(file_slot)
        self.get_information_from_database(sender_id)
        self.slots_record_store = copy.deepcopy(self.slots_record)
        self.custom_records_store = copy.deepcopy(self.custom_records)
        self.pre_action_store = copy.deepcopy(self.pre_action)
        self.cur_action_store = copy.deepcopy(self.cur_action)

    def get_information_from_database(self, sender_id):
        info = dao_user.get(sender_id)
        for key in info:
            tmp = info[key]
            value = tmp["value"]
            if value is not None and value != "null" and value != "NULL" and value != "None":
                self.user_info[key] = tmp

    def reset(self) -> None:
        """
        reset record by action reset conversation
        :return:
        """
        self.__init__(self.sender_id)
        for name_record in self.custom_records:
            self.custom_records[name_record].reset()

    def update_from_tracker(self, tracker: Tracker) -> None:
        """
        from tracker, update params
        self.pre_action
        self.slots_record
        :param tracker:
        :return:
        """

        message_out = tracker.current_state().get("latest_message").get("text")
        self.last_message = message_out

        current_slots = tracker.current_slot_values()
        self.slots_record_store = copy.deepcopy(self.slots_record)
        for slot in current_slots:
            value = current_slots[slot]
            value = value if value is None else str(value)
            if slot not in self.slots_record:
                self.slots_record[slot] = []
            self.slots_record[slot].append(value)

    def update(self, tracker: Tracker, cur_action: Text, cur_intent: Text) -> None:
        """"""
        self.cur_intent = copy.deepcopy(cur_intent)
        if cur_intent is not None:
            self.pre_action = copy.deepcopy(self.cur_action)
            self.cur_action = copy.deepcopy(cur_action)
        # if self.cur_action in reset_actions:
        #     pre_action = self.pre_action
        #     self.reset()
        #     self.pre_action = pre_action
        #     self.cur_action = cur_action

        # if self.cur_action in roll_back_entities:
        #     min_record = 0
        #     for name_record in name_entities_roll_back:
        #         if self.custom_records[name_record].records is not None:
        #             min_record = min(min_record, len(self.custom_records[name_record].records))

        #     for name_record in name_entities_roll_back:
        #         if self.custom_records[name_record].records is not None and len(self.custom_records[name_record].records) > min_record:
        #             self.custom_records[name_record].records = []
                    

        self.update_from_tracker(tracker)
        self.custom_records_store = copy.deepcopy(self.custom_records)
        for name_record in self.custom_records:
            self.custom_records[name_record].update(self)

    def store(self):
        self.slots_record_store = copy.deepcopy(self.slots_record)
        self.custom_records_store = copy.deepcopy(self.custom_records)
        self.pre_action_store = copy.deepcopy(self.pre_action)
        self.cur_action_store = copy.deepcopy(self.cur_action)

    def roll_back(self):
        self.slots_record = copy.deepcopy(self.slots_record_store)
        self.custom_records = copy.deepcopy(self.custom_records_store)
        self.pre_action = copy.deepcopy(self.pre_action_store)
        self.cur_action = copy.deepcopy(self.cur_action_store)

    def get_last_message(self):
        return self.last_message

    def get_last_slot_receive(self, name: Text):
        """
        get slot value from last message received
        :param name: name of slot
        :return:value of slot
        """
        if name not in self.slots_record:
            return None
        return self.slots_record[name][-1]

    def get_last_slot_value(self, name: Text):
        """
        get last slot value not None by tracking
        :param name: naoe of slot
        :return:value of slot
        """
        if name not in self.slots_record:
            return None
        for value in reversed(self.slots_record[name]):
            if value is not None:
                return value
        return None

    def get_current_record(self) -> Dict[Text, Text]:
        """
        get value of record
        :return: dictionary of record items
        """
        result = self.user_info
        for name_record in self.custom_records:
            result[name_record] = self.custom_records[name_record].get_value()
        return result

    def get_user_info_record(self) -> Dict[Text, Text]:
        """
        get value of record
        :return: dictionary of record items
        """
        result = self.user_info
        return result


class RecordManager:
    """
    Recorder for all senders
    """

    def __init__(self):
        """
        init dictionary of recorders for each sender
        """
        self.record_per_user = {}

    def get(self, tracker: Tracker) -> Recorder:
        """
        get Recorder by sender_id
        :param tracker: tracker -> tracker.sender_id
        :return: Recorder(sender_id)
        """
        sender_id = tracker.sender_id
        if sender_id not in self.record_per_user:
            self.record_per_user[sender_id] = Recorder(sender_id)
        return self.record_per_user[sender_id]
