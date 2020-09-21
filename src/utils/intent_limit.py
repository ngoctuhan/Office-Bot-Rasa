import asyncio
import random
import time
import os
from rasa.core.domain import Domain
import pickle
import json
import logging

from config import *

logger = logging.getLogger(__name__)


class Intent_Limitation(object):
    """docstring for Intent_Limitation"""

    def __init__(self):
        """
        self.stories : is graph of stories
        self.intents : is intents which define in NLU
        self.history_send_id : saved history of intent previous which classify user message belong intents
        self.states : is state of user
        """
        with open(PATH_CONFIG, "r") as file_config:
            self.config = json.load(file_config)
        if PATH_CONFIG_GRAPH is None:
            logger.debug("path config not exits")
        else:
            with open(PATH_CONFIG_GRAPH, "rb") as file_config_graph:
                self.stories = pickle.load(file_config_graph)
        if PATH_DOMAIN is None:
            logger.debug("path domain not exits")
        else:
            self.intents = Domain.load(PATH_DOMAIN).intents
        self.history_send_id = {}
        self.states = {}

    def set_history(self, send_id, history):
        # set history of user
        if self.history_send_id.get(send_id) is None:
            self.history_send_id[send_id] = "START"
        else:
            self.history_send_id[send_id] = history

    def normalize_intent(self, name_intents):
        # get name intent.
        name_intents = name_intents.split("/")[-1]
        name_intents = name_intents.split("{")[0]
        return name_intents

    def get_intent(self, send_id):
        # prediction next intents
        result = []
        if self.history_send_id.get(send_id) is None:
            self.history_send_id[send_id] = "START"
        history = self.history_send_id.get(send_id)
        for data in self.stories:
            if data['pre_node'] == history:
                intents_pre = self.normalize_intent(data['intent'])
                if intents_pre in self.intents and not intents_pre in result:
                    result.append(intents_pre)
        return result