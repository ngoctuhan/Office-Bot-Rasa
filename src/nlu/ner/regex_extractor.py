import os
import re
import warnings
from typing import Any, Dict, Optional, Text
from rasa.nlu.config import RasaNLUModelConfig
from rasa.nlu.extractors.extractor import EntityExtractor
from rasa.nlu.model import Metadata
from rasa.nlu.training_data import Message, TrainingData
from rasa.nlu.utils import write_json_to_file
import rasa.utils.io
import logging
import copy
logger = logging.getLogger(__name__)

class RegexEntityExtractor(EntityExtractor):
    # This extractor maybe kind of extreme as it takes user's message
    # and return regex match.
    # Confidence will be 1.0 just like Duckling

    def __init__(
            self,
            component_config: Optional[Dict[Text, Text]] = None,
            regex_features: Optional[Dict[Text, Any]] = None
    ) -> None:
        super(RegexEntityExtractor, self).__init__(component_config)

        self.regex_feature = regex_features if regex_features else {}

    def train(
            self, training_data: TrainingData, config: RasaNLUModelConfig, **kwargs: Any
    ) -> None:

        self.regex_feature = training_data.regex_features

    @classmethod
    def load(
            cls,
            meta: Dict[Text, Any],
            model_dir: Optional[Text] = None,
            model_metadata: Optional[Metadata] = None,
            cached_component: Optional["RegexEntityExtractor"] = None,
            **kwargs: Any
    ) -> "RegexEntityExtractor":

        file_name = meta.get("file")

        if not file_name:
            regex_features = None
            return cls(meta, regex_features)

        # w/o string cast, mypy will tell me
        # expected "Union[str, _PathLike[str]]"
        regex_pattern_file = os.path.join(str(model_dir), file_name)
        if os.path.isfile(regex_pattern_file):
            regex_features = rasa.utils.io.read_json_file(regex_pattern_file)
        else:
            regex_features = None
            warnings.warn(
                "Failed to load regex pattern file from '{}'".format(regex_pattern_file)
            )
        return cls(meta, regex_features)

    def persist(self, file_name: Text, model_dir: Text) -> Optional[Dict[Text, Any]]:
        """Persist this component to disk for future loading."""
        if self.regex_feature:
            file_name = file_name + ".json"
            regex_feature_file = os.path.join(model_dir, file_name)
            write_json_to_file(
                regex_feature_file,
                self.regex_feature, separators=(",", ": "))
            return {"file": file_name}
        else:
            return {"file": None}

    def get_entities_code(self, message):
        arr_mess = message.split(' ')
        code = None
        for i, word in enumerate(arr_mess):
            if word.find('dh')!=-1:
                code = copy.deepcopy(word)
                for j in range(i+1, len(arr_mess)):
                    check = True
                    word_sup = arr_mess[j]
                    for c in word_sup:
                        if c not in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                            check = False
                            break
                    if check == False:
                        break
                    else :
                        code += arr_mess[j]
        if code == 'dh':
            return None
        return code

    def match_regex(self, message):
        """
        regex and get last entity regex-able
        :param message:
        :return: list of entities
        """
        entities = {}
        for d in self.regex_feature:
            pattern = re.compile(f"\\b{d['pattern']}\\b", re.IGNORECASE)
            for match in pattern.finditer(message.lower()):
                name = d['name']
                entity = {
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group(),
                    "confidence": 1.0,
                    "entity": name,
                }
                if name not in entities:
                    entities[name] = []
                entities[name].append(entity)

        code = self.get_entities_code(message)
        if code != None:
            name = "code"
            entity = {
                "start": 1,
                "end": 8,
                "value": code.upper(),
                "confidence": 1.0,
                "entity": name,
            }
            if name not in entities:
                entities[name] = []
            entities[name].append(entity)

        logger.debug(f"--------entities--------{entities}")

        def better(x, y):
            if x["end"] - 1 < y["start"]:
                return x
            if y["end"] - 1 < x["start"]:
                return y
            if len(x["value"]) > len(y["value"]):
                return x
            if len(y["value"]) > len(x["value"]):
                return y
            return y

        extracted = []
        for name in entities:
            list_e = entities[name].copy()
            logging.debug("{} {} {}".format("=" * 20, name, list_e))
            choose = list_e[0]
            for e in list_e[1:]:
                logging.debug("{} {} {}".format("=" * 20, e, choose))
                choose = better(e, choose)
            extracted.append(choose)
        return extracted

    def process(self, message: Message, **kwargs: Any) -> None:
        """Process an incoming message."""
        extracted = self.match_regex(message.text)
        message.set(
            "entities", message.get("entities", []) + extracted, add_to_output=True
        )
