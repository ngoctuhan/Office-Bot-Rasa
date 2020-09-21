import zlib

import base64
import json
import logging
import os
from tqdm import tqdm
from typing import Optional, Any, Dict, List, Text

import rasa.utils.io

from rasa.core.domain import Domain
from rasa.core.events import ActionExecuted
from rasa.core.featurizers import TrackerFeaturizer, MaxHistoryTrackerFeaturizer
from rasa.core.policies.policy import Policy
from rasa.core.trackers import DialogueStateTracker
from rasa.utils.common import is_logging_disabled
from rasa.core.constants import MEMOIZATION_POLICY_PRIORITY

import numpy as np
from src.utils import slot_limit
from src.utils import intent_limit
from src.utils.regex_intent_classifier import RegexIntentClassifier
from src.policies.memoization_custom import Memoization_Custom

from src.utils.recorder import RecordManager
from config import *

recorder_manager = RecordManager()
logger = logging.getLogger(__name__)


class MemoizationPolicy(Policy):
    """The policy that remembers exact examples of
        `max_history` turns from training stories.

        Since `slots` that are set some time in the past are
        preserved in all future feature vectors until they are set
        to None, this policy implicitly remembers and most importantly
        recalls examples in the context of the current dialogue
        longer than `max_history`.

        This policy is not supposed to be the only policy in an ensemble,
        it is optimized for precision and not recall.
        It should get a 100% precision because it emits probabilities of 1.1
        along it's predictions, which makes every mistake fatal as
        no other policy can overrule it.

        If it is needed to recall turns from training dialogues where
        some slots might not be set during prediction time, and there are
        training stories for this, use AugmentedMemoizationPolicy.
    """

    ENABLE_FEATURE_STRING_COMPRESSION = True

    SUPPORTS_ONLINE_TRAINING = True

    USE_NLU_CONFIDENCE_AS_SCORE = False

    @staticmethod
    def _standard_featurizer(max_history=None):
        # Memoization policy always uses MaxHistoryTrackerFeaturizer
        # without state_featurizer
        return MaxHistoryTrackerFeaturizer(
            state_featurizer=None,
            max_history=max_history,
            use_intent_probabilities=False,
        )

    def __init__(
            self,
            featurizer: Optional[TrackerFeaturizer] = None,
            priority: int = MEMOIZATION_POLICY_PRIORITY,
            max_history: Optional[int] = None,
            lookup: Optional[Dict] = None,
    ) -> None:

        if not featurizer:
            featurizer = self._standard_featurizer(max_history)

        super().__init__(featurizer, priority)
        with open(PATH_CONFIG, "r") as file_config:
            self.config = json.load(file_config)
        self.intents_limit = intent_limit.Intent_Limitation()
        self.slots_limit = slot_limit.Slot_Limitation()
        self.regex_classifier = RegexIntentClassifier()
        self.memoi_custom = Memoization_Custom()
        self.max_history = self.featurizer.max_history
        self.lookup = lookup if lookup is not None else {}
        self.is_enabled = True
        self.use_multiple_classifier = self.config.get('use_multiple_classifier')
        self.fallback_intents = self.config.get('fallback_intents')
        self.break_fallback_again = self.config.get('break_fallback_again')
        with open(PATH_CONFIG_FLOW_INTENT, "r") as flow_intent:
            self.flow_intent = json.load(flow_intent)

    def toggle(self, activate: bool) -> None:
        self.is_enabled = activate

    def _add_states_to_lookup(
            self, trackers_as_states, trackers_as_actions, domain, online=False
    ):
        """Add states to lookup dict"""
        if not trackers_as_states:
            return

        assert len(trackers_as_states[0]) == self.max_history, (
            "Trying to mem featurized data with {} historic turns. Expected: "
            "{}".format(len(trackers_as_states[0]), self.max_history)
        )

        assert len(trackers_as_actions[0]) == 1, (
            "The second dimension of trackers_as_action should be 1, "
            "instead of {}".format(len(trackers_as_actions[0]))
        )

        ambiguous_feature_keys = set()

        pbar = tqdm(
            zip(trackers_as_states, trackers_as_actions),
            desc="Processed actions",
            disable=is_logging_disabled(),
        )
        for states, actions in pbar:
            action = actions[0]

            feature_key = self._create_feature_key(states)
            feature_item = domain.index_for_action(action)

            if feature_key not in ambiguous_feature_keys:
                if feature_key in self.lookup.keys():
                    if self.lookup[feature_key] != feature_item:
                        if online:
                            logger.info(
                                "Original stories are "
                                "different for {} -- {}\n"
                                "Memorized the new ones for "
                                "now. Delete contradicting "
                                "examples after exporting "
                                "the new stories."
                                "".format(states, action)
                            )
                            self.lookup[feature_key] = feature_item
                        else:
                            # delete contradicting example created by
                            # partial history augmentation from memory
                            ambiguous_feature_keys.add(feature_key)
                            del self.lookup[feature_key]
                else:
                    self.lookup[feature_key] = feature_item
            pbar.set_postfix({"# examples": "{:d}".format(len(self.lookup))})

    def _create_feature_key(self, states: List[Dict]) -> Text:
        from rasa.utils import io

        feature_str = json.dumps(states, sort_keys=True).replace('"', "")
        if self.ENABLE_FEATURE_STRING_COMPRESSION:
            compressed = zlib.compress(bytes(feature_str, io.DEFAULT_ENCODING))
            return base64.b64encode(compressed).decode(io.DEFAULT_ENCODING)
        else:
            return feature_str

    def train(
            self,
            training_trackers: List[DialogueStateTracker],
            domain: Domain,
            **kwargs: Any,
    ) -> None:
        """Trains the policy on given training trackers."""
        self.lookup = {}
        # only considers original trackers (no augmented ones)
        training_trackers = [
            t
            for t in training_trackers
            if not hasattr(t, "is_augmented") or not t.is_augmented
        ]
        (
            trackers_as_states,
            trackers_as_actions,
        ) = self.featurizer.training_states_and_actions(training_trackers, domain)
        self._add_states_to_lookup(trackers_as_states, trackers_as_actions, domain)
        logger.debug("Memorized {} unique examples.".format(len(self.lookup)))

    def continue_training(
            self,
            training_trackers: List[DialogueStateTracker],
            domain: Domain,
            **kwargs: Any,
    ) -> None:

        # add only the last tracker, because it is the only new one
        (
            trackers_as_states,
            trackers_as_actions,
        ) = self.featurizer.training_states_and_actions(training_trackers[-1:], domain)
        self._add_states_to_lookup(trackers_as_states, trackers_as_actions, domain)

    def _recall_states(self, states: List[Dict[Text, float]]) -> Optional[int]:

        return self.lookup.get(self._create_feature_key(states))

    def recall(
            self,
            states: List[Dict[Text, float]],
            tracker: DialogueStateTracker,
            domain: Domain,
    ) -> Optional[int]:

        return self._recall_states(states)

    def change_confidence_if_start(self, tracker: DialogueStateTracker) -> None:
        send_id = tracker.sender_id
        if self.intents_limit.history_send_id.get(send_id) == "START" or self.intents_limit.history_send_id.get(
                send_id) is None:
            check = False
            # history save position node in graph
            # if user is first node then intent is greet
            for i, intent_tmp in enumerate(tracker.latest_message.parse_data['intent_ranking']):
                # if intent_tmp['name'] == "greet":
                if intent_tmp['name'] in self.config.get('name_intent_start'):
                    tracker.latest_message.parse_data['intent_ranking'][i]['confidence'] = 1.0
                    check = True
                    break
            if check == False:
                tracker.latest_message.parse_data['intent_ranking'].append({'name': 'null_intent', 'confidence': 1.0})

    def change_flow_by_user_info(self, tracker: DialogueStateTracker, action_predict, intent_name):
        """

        :param tracker: Tracker from rasa
        :param action_predict: action_predict after run intent_classifier
        :param intent_name: intent_predict after run intent_classifier
        :return: new intent after change flow
        """
        send_id = tracker.sender_id
        intent_pre = self.intents_limit.get_intent(send_id)
        recorder = recorder_manager.get(tracker)
        last_intent = recorder.cur_intent
        recorder.store()
        recorder.update(tracker, action_predict, intent_name)
        record = recorder.get_current_record()
        new_name_intent = intent_name
        change_flow = False
        if intent_name in self.flow_intent:
            for new_intent in self.flow_intent[intent_name]["new_intents"]:
                property = new_intent["property"]
                if property in record:
                    if isinstance(record[property], dict):
                        type_user = record[property]["value"]
                    else:
                        type_user = record[property]
                else:
                    type_user = None
                if new_intent["name"] in intent_pre and (
                        new_intent["type"] == type_user or new_intent["type"] == "anything"):
                    new_name_intent = new_intent["name"]
                    change_flow = True
                    break
        if (new_name_intent in self.fallback_intents) and (last_intent in self.fallback_intents) and (
                self.break_fallback_again is True):
            if "intent_fallback_again" in intent_pre:
                new_name_intent = "intent_fallback_again"
                change_flow = True
        recorder.roll_back()
        return new_name_intent, change_flow

    def change_confidence_by_custom_model(self, tracker: DialogueStateTracker) -> None:
        intent_real = {"name": "", "confidence": 0}
        send_id = tracker.sender_id
        intent_pre = self.intents_limit.get_intent(send_id)  # prediction intents will occur
        logger.debug(f"Intent limit area: {intent_pre}")
        logger.debug(f"Intent ranking BEFORE: {tracker.latest_message.parse_data['intent_ranking']}")
        mess = tracker.latest_message.parse_data['text']

        # if self.use_multiple_classifier is True:
        #     intent_confidence = self.multiple_nlu_classifier.process(mess)
        #     for i, intent_tmp in enumerate(tracker.latest_message.parse_data['intent_ranking']):
        #         intent_name = intent_tmp['name']
        #         confidence = intent_confidence.get(intent_name) if intent_name in intent_confidence else 0.0
        #         if intent_name != "null_intent":
        #             tracker.latest_message.parse_data['intent_ranking'][i]['confidence'] = confidence
        #     logger.debug(f"Intent confidence by multi classifier: {intent_confidence}")

        # set up parameter intent classification [confidence].
        state_regex = True
        for i, intent_tmp in enumerate(tracker.latest_message.parse_data['intent_ranking']):
            if intent_tmp['name'] not in intent_pre:
                tracker.latest_message.parse_data['intent_ranking'][i]['confidence'] = 0
            else:
                label_regex = self.regex_classifier.predict_name_intent(mess, intent_tmp['name'])
                # logger.debug(f"{intent_tmp['name']} | label_predict: {label_regex}")
                if label_regex is not None and state_regex:
                    tracker.latest_message.parse_data['intent_ranking'][i]['confidence'] = 1.0
                    intent_real['confidence'] = 1.0
                    intent_real['name'] = intent_tmp['name']
                    state_regex = False
                else:
                    if intent_real['confidence'] < intent_tmp['confidence']:
                        intent_real = intent_tmp
                    else:
                        tracker.latest_message.parse_data['intent_ranking'][i]['confidence'] = 0.0

        # Process intent fallback
        if intent_real['confidence'] < self.config.get('confidence_intent_fallback'):
            intent_real['name'] = "intent_fallback"
            intent_real['confidence'] = 1.0
            for i, intent_tmp in enumerate(tracker.latest_message.parse_data['intent_ranking']):
                if intent_tmp['name'] == intent_real['name']:
                    tracker.latest_message.parse_data['intent_ranking'][i]['confidence'] = 1.0
                else:
                    tracker.latest_message.parse_data['intent_ranking'][i]['confidence'] = 0.0

        tracker.latest_message.parse_data['intent'] = intent_real
        # logger.debug(f"Intent ranking AFTER: {tracker.latest_message.parse_data['intent_ranking']}")
        logger.debug(f"Intent after regex classification and fallback: {intent_real}")

    def change_slots_with_slots_limit(self, tracker: DialogueStateTracker) -> None:
        # Process slot limit
        limited_slots = self.slots_limit.get_limited_slots(tracker.latest_message.parse_data['intent']['name'])
        self.slots_limit.remove_unallowed_slots_from_tracker(tracker, limited_slots)
        logger.debug(f"Slots after slot limit: {tracker.current_slot_values()}")
        logger.debug(f"Entities after slot limit: {tracker.latest_message.entities}")

    def predict_action_probabilities(
            self, tracker: DialogueStateTracker, domain: Domain
    ) -> List[float]:
        """Predicts the next action the bot should take
            after seeing the tracker.

            Returns the list of probabilities for the next actions.
            If memorized action was found returns 1.1 for its index,
            else returns 0.0 for all actions."""
        result = [0.0] * domain.num_actions
        # print (domain.user_actions)

        if not self.is_enabled:
            return result
        send_id = tracker.sender_id  # get id of user send message
        if self.intents_limit.history_send_id.get(send_id) is None:
            self.intents_limit.states[send_id] = True

        if self.intents_limit.states.get(send_id) is True and not tracker.latest_message.parse_data['text'].startswith(
                '/'):
            # self.change_confidence_if_start(tracker)
            self.change_confidence_by_custom_model(tracker)
            self.change_slots_with_slots_limit(tracker)
            # state of set up parameter of intent rank

        name_intent = tracker.latest_message.parse_data['intent']['name']
        name_entities = []
        for tmp_entites in tracker.latest_message.entities:
            entities_real = tmp_entites.get('entity')
            if entities_real is not None and not entities_real in name_entities:
                name_entities.append(entities_real)
        pre_action = self.intents_limit.history_send_id.get(send_id)
        action_predict = self.memoi_custom.get_next_action(pre_action, name_intent, name_entities)

        if self.intents_limit.states[send_id] is True:
            if action_predict is None:
                action_predict = "action_quit"
            else:
                logger.debug(f"ACTION PREDICT BEFORE CHANGE FLOW: {name_intent} {action_predict}")
                new_intent_name, change_flow = self.change_flow_by_user_info(tracker, action_predict, name_intent)
                if change_flow is True:
                    action_predict = self.memoi_custom.get_next_action(pre_action, new_intent_name, [])
                recorder = recorder_manager.get(tracker)
                recorder.update(tracker, action_predict, new_intent_name)
                logger.debug(f"ACTION PREDICT AFTER CHANGE FLOW: {new_intent_name} {action_predict}")
            index_action = domain.action_names.index(action_predict)
            result[index_action] = 1.0
        else:
            index_action = domain.action_names.index("action_listen")
            result[index_action] = 1.0
        # logger.debug(f"Confidence final: {tracker.latest_message.parse_data}")
        result_np = result
        index = np.where(result_np)[0]
        if index is not None and len(index) > 0:
            index = index[0].tolist()
            actions_next = domain.action_names[index]
            # logger.debug(f"Next action..............: {actions_next}")
            if actions_next in domain.user_actions:
                # action_pre is in which is action in domain.yml
                if actions_next in self.config.get('name_action_finsh'):
                    # logger.debug("{}{}{}".format("=" * 50 , "RESTART", "="))
                    self.intents_limit.set_history(send_id, "START")
                    self.intents_limit.states[send_id] = True
                else:
                    if actions_next not in self.config.get('name_action_back'):
                        self.intents_limit.set_history(send_id, actions_next)
                    self.intents_limit.states[send_id] = False
            else:
                # action_pre is [action listen] and not action in domain.yml
                self.intents_limit.states[send_id] = True
        else:
            # action_pre is not use memorization (use fallback)
            self.intents_limit.set_history(send_id, "START")
            self.intents_limit.states[send_id] = True
        return result

    def persist(self, path: Text) -> None:

        self.featurizer.persist(path)

        memorized_file = os.path.join(path, "memorized_turns.json")
        data = {
            "priority": self.priority,
            "max_history": self.max_history,
            "lookup": self.lookup,
        }
        rasa.utils.io.create_directory_for_file(memorized_file)
        rasa.utils.io.dump_obj_as_json_to_file(memorized_file, data)

    @classmethod
    def load(cls, path: Text) -> "MemoizationPolicy":

        featurizer = TrackerFeaturizer.load(path)
        memorized_file = os.path.join(path, "memorized_turns.json")
        if os.path.isfile(memorized_file):
            data = json.loads(rasa.utils.io.read_file(memorized_file))
            return cls(
                featurizer=featurizer, priority=data["priority"], lookup=data["lookup"]
            )
        else:
            logger.info(
                "Couldn't load memoization for policy. "
                "File '{}' doesn't exist. Falling back to empty "
                "turn memory.".format(memorized_file)
            )
            return cls()


class AugmentedMemoizationPolicy(MemoizationPolicy):
    """The policy that remembers examples from training stories
        for `max_history` turns.

        If it is needed to recall turns from training dialogues
        where some slots might not be set during prediction time,
        add relevant stories without such slots to training data.
        E.g. reminder stories.

        Since `slots` that are set some time in the past are
        preserved in all future feature vectors until they are set
        to None, this policy has a capability to recall the turns
        up to `max_history` from training stories during prediction
        even if additional slots were filled in the past
        for current dialogue.
    """

    @staticmethod
    def _back_to_the_future_again(tracker):
        """Send Marty to the past to get
            the new featurization for the future"""

        idx_of_first_action = None
        idx_of_second_action = None

        # we need to find second executed action
        for e_i, event in enumerate(tracker.applied_events()):
            # find second ActionExecuted
            if isinstance(event, ActionExecuted):
                if idx_of_first_action is None:
                    idx_of_first_action = e_i
                else:
                    idx_of_second_action = e_i
                    break

        if idx_of_second_action is None:
            return None
        # make second ActionExecuted the first one
        events = tracker.applied_events()[idx_of_second_action:]
        if not events:
            return None

        mcfly_tracker = tracker.init_copy()
        for e in events:
            mcfly_tracker.update(e)

        return mcfly_tracker

    def _recall_using_delorean(self, old_states, tracker, domain):
        """Recursively go to the past to correctly forget slots,
            and then back to the future to recall."""

        logger.debug("Launch DeLorean...")
        mcfly_tracker = self._back_to_the_future_again(tracker)
        while mcfly_tracker is not None:
            tracker_as_states = self.featurizer.prediction_states(
                [mcfly_tracker], domain
            )
            states = tracker_as_states[0]

            if old_states != states:
                # check if we like new futures
                memorised = self._recall_states(states)
                if memorised is not None:
                    logger.debug(f"Current tracker state {states}")
                    return memorised
                old_states = states

            # go back again
            mcfly_tracker = self._back_to_the_future_again(mcfly_tracker)

        # No match found
        logger.debug(f"Current tracker state {old_states}")
        return None

    def recall(
            self,
            states: List[Dict[Text, float]],
            tracker: DialogueStateTracker,
            domain: Domain,
    ) -> Optional[int]:

        recalled = self._recall_states(states)
        if recalled is None:
            # let's try a different method to recall that tracker
            return self._recall_using_delorean(states, tracker, domain)
        else:
            return recalled