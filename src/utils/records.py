from typing import Any, Dict, Iterator, List, Optional, Text
import copy
import logging


logger = logging.getLogger(__name__)

class ImplRecord:
    def __init__(self):
        self.records = []

    def update(self, recorder) -> None:
        """
        check_update and update from values of recorder
        :param recorder: Recorder
        :return: None
        """
        raise NotImplementedError("An record must implement its update method")

    def get_value(self):
        """
        get value of item recorded
        :return:Text recorded
        """
        raise NotImplementedError("An record must implement its get method")

    def reset(self) -> None:
        """
        reset value of item record when recorder run reset
        :return: None
        """
        raise NotImplementedError("An record must implement its reset method")


# class AmountRecord(ImplRecord):
#     def reset(self) -> None:
#         self.records = []

#     def update(self, recorder) -> None:
#         value = recorder.get_last_slot_value("amount")
#         self.records.append(value)

#     def get_value(self) -> Text:
#         return self.records[-1]
#         