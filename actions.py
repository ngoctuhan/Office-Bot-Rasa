from typing import Text

from rasa_sdk import Action
from rasa_sdk.events import Restarted
import json
import logging
import copy

from src.utils.recorder import RecordManager
from config import *

logger = logging.getLogger(__name__)

with open(PATH_CONFIG_TEMPLATE_ACTION, "r", encoding='utf-8') as file_action:
    action_template = json.load(file_action, encoding='utf-8')

record_manager = RecordManager()


def execute_normal_action(tracker, cur_action):
    """
    execute action for all actions includes:
    - update records from tracker
    - get action response from action_template
    - format response message
    :param tracker: rasa tracker
    :param cur_action: current action
    :return: response
    """
    global action_template, record_manager
    responses = copy.deepcopy(action_template[cur_action])
    cur_intent = tracker.latest_message['intent'].get('name')
    recorder = record_manager.get(tracker)
    recorder.update(tracker, cur_action, cur_intent)
    pre_action = recorder.pre_action
    record = recorder.get_current_record()

    def get_action_response():
        response_ans = responses[0]
        for response_id in responses:
            if "properties" in response_id:
                properties = response_id["properties"]
                check_properties = True
                for p in properties:
                    value = properties[p]
                    # logger.debug("=" * 50 + str(properties) + " " + str(record[p]))
                    if p in record:
                        if isinstance(record[p], dict):
                            value_recorded = record[p]["value"]
                        else:
                            value_recorded = record[p]
                        if value_recorded != value:
                            check_properties = False
                            break
                if check_properties:
                    response_ans = response_id
                    break
            else:
                response_ans = response_id
                break
        # logger.debug("="*50 + str(response_ans))
        return response_ans

    def format_text(text, record):
        for key in record:
            if isinstance(record[key], dict):
                text = text.replace("{" + str(key) + "}", str(record[key]["text"]))
            else:
                text = text.replace("{" + str(key) + "}", str(record[key]))
        return text

    logging.debug(record)
    response = get_action_response()
    text = response["text"]
    text_tts = response["text_tts"]
    # text_tts = text  # get_action_response(pre_action, "text_tts")

    response["text"] = format_text(text, record)
    response["text_tts"] = format_text(text_tts, record)
    response["action"] = cur_action
    response["intent"] = cur_intent

    return json.dumps(response)


class action_hellow(Action):
    def name(self) -> Text:
        return "action_hellow"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]

class action_bye(Action):
    def name(self) -> Text:
        return "action_bye"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_laudatory(Action):
    def name(self) -> Text:
        return "action_laudatory"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_condition(Action):
    def name(self) -> Text:
        return "action_condition"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_brief(Action):
    def name(self) -> Text:
        return "action_brief"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_step_interview(Action):
    def name(self) -> Text:
        return "action_step_interview"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_old(Action):
    def name(self) -> Text:
        return "action_old"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_club(Action):
    def name(self) -> Text:
        return "action_club"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_laptop(Action):
    def name(self) -> Text:
        return "action_laptop"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_resignation(Action):
    def name(self) -> Text:
        return "action_resignation"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_employee(Action):
    def name(self) -> Text:
        return "action_employee"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_englishDegree(Action):
    def name(self) -> Text:
        return "action_englishDegree"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_exp(Action):
    def name(self) -> Text:
        return "action_exp"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_fields(Action):
    def name(self) -> Text:
        return "action_fields"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_GPA(Action):
    def name(self) -> Text:
        return "action_GPA"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_health(Action):
    def name(self) -> Text:
        return "action_health"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_holiday(Action):
    def name(self) -> Text:
        return "action_holiday"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_overtime(Action):
    def name(self) -> Text:
        return "action_overtime"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_salary(Action):
    def name(self) -> Text:
        return "action_salary"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_sport(Action):
    def name(self) -> Text:
        return "action_sport"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_submitCV(Action):
    def name(self) -> Text:
        return "action_submitCV"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_timework(Action):
    def name(self) -> Text:
        return "action_timework"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_trainning(Action):
    def name(self) -> Text:
        return "action_trainning"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_where(Action):
    def name(self) -> Text:
        return "action_where"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_partTime(Action):
    def name(self) -> Text:
        return "action_partTime"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_maternity(Action):
    def name(self) -> Text:
        return "action_maternity"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_canteen(Action):
    def name(self) -> Text:
        return "action_canteen"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_commit(Action):
    def name(self) -> Text:
        return "action_commit"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_degree(Action):
    def name(self) -> Text:
        return "action_degree"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]
class action_insurrance(Action):
    def name(self) -> Text:
        return "action_insurrance"

    def run(self, dispatcher, tracker, domain):
        response = execute_normal_action(tracker, self.name())
        dispatcher.utter_message(text=response)
        return [Restarted()]