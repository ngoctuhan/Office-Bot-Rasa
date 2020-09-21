import json
import os
import random
import rasa.nlu.classifiers.embedding_intent_classifier
import re

from config import *


class RegexIntentClassifier(object):
    """docstring for Intent_Classification"""

    def __init__(self):
        config_file = PATH_CONFIG_REGEX
        with open(config_file, encoding='utf8') as file_regex:
            self.intents = json.load(file_regex)
        super(RegexIntentClassifier, self).__init__()

    def predict(self, message):
        for name_intent in self.intents:
            for re_str in self.intents[name_intent]['regex']:
                if re.match(".*{}.*".format(re_str), message, re.IGNORECASE):
                    return name_intent
        return None

    def predict_name_intent(self, message, name_intent):
        if self.intents.get(name_intent) is None:
            return None
        for re_str in self.intents[name_intent]['regex']:
            if re.match(".*{}.*".format(re_str), message, re.IGNORECASE):
                return name_intent
        return None