import json
from typing import Optional, Any, Dict, List, Text
from rasa.core.trackers import DialogueStateTracker
from rasa.core.events import (  # pytype: disable=pyi-error
    SlotSet
)
import logging

from config import *


class Slot_Limitation(object):
    """docstring for Slot_Limitation"""

    def __init__(self):
        """
        self.slot_limit_dict : Dictionary that key is intent name, value is list of limited slots
        """
        with open(PATH_CONFIG_LIMITS_SLOTS, 'r') as file_slot_limit:
            self.slot_limit_dict = json.load(file_slot_limit)

    def get_limited_slots(self, intent_name):
        if intent_name in self.slot_limit_dict:
            return self.slot_limit_dict[intent_name]
        return []

    def remove_unallowed_slots_from_tracker(self, tracker: DialogueStateTracker, limited_slots: List) -> None:
        self._remove_slots(tracker, limited_slots)
        self._remove_entities(tracker, limited_slots)
        self._remove_events(tracker, limited_slots)

    def _remove_slots(self, tracker: DialogueStateTracker, limited_slots: List) -> None:
        for key, slot in tracker.slots.items():
            if key not in limited_slots:
                tracker.slots[key].value = None

    def _remove_entities(self, tracker: DialogueStateTracker, limited_slots: List) -> None:
        def remove_conflict_entities(entities):
            """
            Params : tracker, limited_slots: a list of slots - init entities
            Return : a list of entities has been removed the conflict entity
            """
            entities_remove_conflict = []
            poss = {}
            for idx1, e1 in enumerate(entities):
                is_conflict = False
                for idx2, e2 in enumerate(entities):
                    if idx1 != idx2:
                        is_inside = e1["start"] >= e2["start"] and e1["end"] <= e2["end"]
                        is_different = e1["start"] != e2["start"] or e1["end"] != e2["end"]
                        is_available = (e1["start"], e1["end"]) in poss
                        if is_inside and (is_different or is_available):
                            is_conflict = True
                            break
                if not is_conflict:
                    entities_remove_conflict.append(e1)
                    poss[(e1["start"], e1["end"])] = 1
            return entities_remove_conflict

        new_entities = []
        for entity in tracker.latest_message.entities:
            if entity['entity'] in limited_slots:
                new_entities.append(entity)
        new_entities = remove_conflict_entities(new_entities)

        limited_slots_remove_conflict = []
        for entity in new_entities:
            limited_slots_remove_conflict.append(entity['entity'])
        self._remove_slots(tracker, limited_slots_remove_conflict)

        tracker.latest_message.entities = new_entities
        tracker.latest_message.parse_data['entities'] = new_entities

    def _remove_events(self, tracker: DialogueStateTracker, limited_slots: List) -> None:
        slot_set_events = []
        while len(tracker.events) > 0 and isinstance(tracker.events[-1], SlotSet):
            slot_set_events.append(tracker.events[-1])
            tracker.events.pop()
        for event in slot_set_events[::-1]:
            if event.key in limited_slots:
                tracker.events.append(event)