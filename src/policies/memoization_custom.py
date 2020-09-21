import asyncio
import random
import time
import os
from rasa.core.domain import Domain
import pickle
import json

from config import *

def normalization_intents(name_intents):
    """
    get name of intent
    :param name_intents: name_intent with entities format
    :return: name of intent and name of entities
    """
    name_intent_all = name_intents.split("/")[-1]
    name_intent = name_intent_all.split("{")[0]
    name_entities = []
    if len(name_intent_all.split("{")) > 1:
        entities = name_intent_all.split("{")[-1]
        entities = "{" + entities
        entities = eval(entities)
        for x in entities:
            name_entities.append(x)
    else:
        name_entities = None
    return name_intent, name_entities


class Memoization_Custom(object):
    """docstring for Intent_Limitation"""

    def __init__(self):
        """self.stories: graph of stories"""
        with open(PATH_CONFIG_GRAPH, "rb") as file_config_graph:
            self.stories = pickle.load(file_config_graph)
        self.graph_stories = {}
        self.save_stories()

    def get_next_action(self, action_pre, name_intent, name_entities):
        if self.graph_stories.get(action_pre) is None:
            return None
        if self.graph_stories.get(action_pre).get(name_intent) is None:
            return None
        if name_entities is None or len(name_entities) == 0:
            if self.graph_stories.get(action_pre).get(name_intent).get('not_entities') is None:
                return None
            return self.graph_stories.get(action_pre).get(name_intent).get('not_entities').get('action')
        name_entities = sorted(name_entities)

        if self.graph_stories.get(action_pre).get(name_intent).get(tuple(name_entities)) is None:
            return None
        return self.graph_stories.get(action_pre).get(name_intent).get(tuple(name_entities)).get('action')

    def save_stories(self):
        for data in self.stories:
            pre_node = data['pre_node']
            intent = data['intent']
            cur_node = data['cur_node']
            name_intent, name_entities = normalization_intents(intent)
            if name_entities is None:
                if self.graph_stories.get(pre_node) is None:
                    self.graph_stories[pre_node] = {}
                    self.graph_stories[pre_node][name_intent] = {}
                    self.graph_stories[pre_node][name_intent]['not_entities'] = {}
                    self.graph_stories[pre_node][name_intent]['not_entities']['action'] = {}
                    self.graph_stories[pre_node][name_intent]['not_entities']['action'] = cur_node
                else:
                    if self.graph_stories.get(pre_node).get(name_intent) is None:
                        self.graph_stories[pre_node][name_intent] = {}
                        self.graph_stories[pre_node][name_intent]['not_entities'] = {}
                        self.graph_stories[pre_node][name_intent]['not_entities']['action'] = {}
                        self.graph_stories[pre_node][name_intent]['not_entities']['action'] = cur_node
                    else:
                        if self.graph_stories.get(pre_node).get(name_intent).get('not_entities') is None:
                            self.graph_stories[pre_node][name_intent]['not_entities'] = {}
                            self.graph_stories[pre_node][name_intent]['not_entities']['action'] = {}
                            self.graph_stories[pre_node][name_intent]['not_entities']['action'] = cur_node
                        else:
                            if self.graph_stories.get(pre_node).get(pre_node).get('not_entities').get(
                                    'action') != cur_node:
                                print("-----------------fail--------------------")
                                return 0
            else:
                name_entities = sorted(name_entities)
                if self.graph_stories.get(pre_node) is None:
                    self.graph_stories[pre_node] = {}
                    self.graph_stories[pre_node][name_intent] = {}
                else:
                    if self.graph_stories.get(pre_node).get(name_intent) is None:
                        self.graph_stories[pre_node][name_intent] = {}
                if self.graph_stories[pre_node][name_intent].get(tuple(name_entities)) is None:
                    self.graph_stories[pre_node][name_intent][tuple(name_entities)] = {}
                    self.graph_stories[pre_node][name_intent][tuple(name_entities)]['action'] = cur_node
                else:
                    if self.graph_stories[pre_node][name_intent][tuple(name_entities)].get('action') != cur_node:
                        print("-----------------fail--------------------")
                        return 0