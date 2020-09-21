import logging
import uuid
import inspect
import rasa
from sanic import Blueprint, response
from sanic.request import Request
from socketio import AsyncServer
from typing import Text, List, Dict, Any, Optional, Callable, Iterable, Awaitable
from asyncio import Queue, CancelledError
from rasa.core.channels.channel import UserMessage, OutputChannel, CollectingOutputChannel, InputChannel, \
    QueueOutputChannel

import asyncio
import inspect
import json
import logging
import uuid
from asyncio import Queue, CancelledError
from sanic import Sanic, Blueprint, response
from sanic.request import Request
from typing import Text, List, Dict, Any, Optional, Callable, Iterable, Awaitable

import rasa.utils.endpoints
from rasa.cli import utils as cli_utils
from rasa.constants import DOCS_BASE_URL
from rasa.core import utils
from sanic.response import HTTPResponse
from rasa.core.domain import Domain
import mysql.connector as mysql_db
import csv

from rasa.core.domain import TemplateDomain
from rasa.core.training.dsl import StoryFileReader
from rasa.core.training.visualization import visualize_stories
from rasa.core.training import visualization
import asyncio
import random
import time
from rasa.core.training.structures import StoryGraph
import networkx as nx
import os
import pickle
import json

from config import *

logger = logging.getLogger(__name__)


class RestInputCustom(InputChannel):
    """A custom http input channel.

    This implementation is the basis for a custom implementation of a chat
    frontend. You can customize this to send messages to Rasa Core and
    retrieve responses from the agent."""

    def __init__(self):
        with open(PATH_CONFIG, "r") as file_config:
            self.config = json.load(file_config)
        self.name_table_history = self.config.get("database").get("name_table_history")
        self.name_table_user = self.config.get("database").get("name_table_user")
        # self.path_domain = self.config.get("path_domain")
        self.path_domain = PATH_DOMAIN
        self.domain = Domain.load(self.path_domain)
        self.connect = mysql_db.connect(host=self.config.get("database").get("host"),
                                        username=self.config.get("database").get("username"),
                                        password=self.config.get("database").get("password"),
                                        db=self.config.get("database").get("db"),
                                        port=self.config.get("database").get("port"))
        self.connect.autocommit = True
        with open(PATH_CONFIG_USER_PARAMS, "r") as file_slot:
            self.reader_config_slots = json.load(file_slot)
        with open(PATH_CONFIG_GRAPH, "rb") as file_config:
            self.result_stories = pickle.load(file_config)
        with open(PATH_CONFIG_TEMPLATE_ACTION, "r") as file:
            self.data_template = json.load(file)

    @classmethod
    def name(cls) -> Text:
        return "rest_custom"

    @staticmethod
    async def on_message_wrapper(
            on_new_message: Callable[[UserMessage], Awaitable[Any]],
            text: Text,
            queue: Queue,
            sender_id: Text,
            input_channel: Text,
            metadata: Optional[Dict[Text, Any]],
    ) -> None:
        collector = QueueOutputChannel(queue)

        message = UserMessage(
            text, collector, sender_id, input_channel=input_channel, metadata=metadata
        )
        await on_new_message(message)

        await queue.put("DONE")  # pytype: disable=bad-return-type

    async def _extract_sender(self, req: Request) -> Optional[Text]:
        return req.json.get("sender", None)

    # noinspection PyMethodMayBeStatic
    def _extract_message(self, req: Request) -> Optional[Text]:
        return req.json.get("message", None)

    def _extract_input_channel(self, req: Request) -> Text:
        return req.json.get("input_channel") or self.name()

    def stream_response(
            self,
            on_new_message: Callable[[UserMessage], Awaitable[None]],
            text: Text,
            sender_id: Text,
            input_channel: Text,
            metadata: Optional[Dict[Text, Any]],
    ) -> Callable[[Any], Awaitable[None]]:
        async def stream(resp: Any) -> None:
            q = Queue()
            task = asyncio.ensure_future(
                self.on_message_wrapper(
                    on_new_message, text, q, sender_id, input_channel, metadata
                )
            )
            result = None  # declare variable up front to avoid pytype error
            while True:
                result = await q.get()
                if result == "DONE":
                    break
                else:
                    await resp.write(json.dumps(result) + "\n")
            await task

        return stream  # pytype: disable=bad-return-type

    def blueprint(
            self, on_new_message: Callable[[UserMessage], Awaitable[None]]
    ) -> Blueprint:
        custom_webhook = Blueprint(
            "custom_webhook_{}".format(type(self).__name__),
            inspect.getmodule(self).__name__,
        )

        # noinspection PyUnusedLocal
        @custom_webhook.route("/", methods=["GET"])
        async def health(request: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        # getIntents
        @custom_webhook.route("/getIntents", methods=["GET"])
        async def get_intents(request: Request) -> HTTPResponse:
            list_intents = self.domain.intents
            return response.json({
                "status": 0,
                "msg": "Success",
                "intents": list_intents,
            })

        # getEntitites
        @custom_webhook.route("/getEntities", methods=["GET"])
        async def get_entities(request: Request) -> HTTPResponse:
            list_entities = self.domain.entities
            print(self.domain)
            return response.json({
                "status": 0,
                "msg": "Success",
                "entities": list_entities,
            })

        # getActions
        @custom_webhook.route("/getActions", methods=["GET"])
        async def get_actions(request: Request) -> HTTPResponse:
            list_actions = self.domain.user_actions
            return response.json({
                "status": 0,
                "msg": "Success",
                "actions": list_actions,
            })

        # inputSlots
        @custom_webhook.route("/inputSlots", methods=["GET"])
        async def input_slots(request: Request) -> HTTPResponse:
            list_slots = []
            for name_slot in self.reader_config_slots.get('slots'):
                list_slots.append(name_slot)

            return response.json({
                "status": 0,
                "msg": "Success",
                "inputSlots": list_slots,
            })

        # inputSlots
        @custom_webhook.route("/getTemplateAction", methods=["POST"])
        async def get_template_action(request: Request) -> HTTPResponse:
            # self.connect.ping(reconnect = True)
            # mycursor = self.connect.cursor()
            # sql = "SELECT * FROM "
            # sql += self.name_table_user + " WHERE id_conversation like %s"
            # id_conversation = request.json.get("id_conversation")
            # mycursor.execute(sql, [id_conversation])
            # myresult = mycursor.fetchall()
            # if len(myresult) > 0:
            #     for x in myresult:
            #         name = x[2]
            #         honor = x[3]
            #         phone_number = x[4]
            #         remain_money = x[5]
            #         used_money = x[6]
            #         date = x[7]
            # else :
            #     return response.json({
            #         "status": 0,
            #         "msg" : "Success",
            #         "action_template": [],
            #     })
            result = []
            for name_tmp in self.data_template:
                for temp in self.data_template[name_tmp]:
                    x = temp['text_tts']
                    if not x in result:
                        result.append(x)
            return response.json({
                "status": 0,
                "msg": "Success",
                "action_template": result,
            })

        # getStories
        @custom_webhook.route("/getStories", methods=["GET"])
        async def get_stories(request: Request) -> HTTPResponse:
            self.connect.ping(reconnect=True)
            mycursor = self.connect.cursor()
            sql = "SELECT pre_action, action_name, intent_name FROM "
            sql += self.name_table_history
            mycursor.execute(sql)

            myresult = mycursor.fetchall()
            check = {}
            total = 0

            for x in myresult:
                total += 1
                tmp = "/" + x[2]
                if check.get(x[0]) is None:
                    check[x[0]] = {}
                    check[x[0]][x[1]] = {}
                    check[x[0]][x[1]][tmp] = 1
                else:
                    if check.get(x[0]).get(x[1]) is None:
                        check[x[0]][x[1]] = {}
                        check[x[0]][x[1]][tmp] = 1
                    else:
                        if check.get(x[0]).get(x[1]).get(tmp) is None:
                            check[x[0]][x[1]][tmp] = 1
                        else:
                            check[x[0]][x[1]][tmp] += 1

            result_edges = self.result_stories

            for x in result_edges:
                pre_node = x['pre_node']
                cur_node = x['cur_node']
                intent = x['intent']
                if check.get(pre_node) is not None and check.get(pre_node).get(cur_node) is not None and check.get(
                        pre_node).get(cur_node).get(intent) is not None:
                    x['count'] = check.get(pre_node).get(cur_node).get(intent)
            list_nodes = ["START"] + self.domain.user_actions + ["END"]
            return response.json({
                "status": 0,
                "msg": "Success",
                "nodes": list_nodes,
                "edges": result_edges,
                "total_conversation": total
            })

        # # initialize of calling
        @custom_webhook.route("/initCall", methods=["POST"])
        async def get_slots(request: Request) -> HTTPResponse:
            self.connect.ping(reconnect=True)
            id_conversation = request.json.get("id_conversation")
            # input_slots = request.json.get("input_slots")
            # name = input_slots['name']
            # num_phone = input_slots['num_phone']
            # honor = input_slots['honor']
            # remain_amount = input_slots['remain_amount']
            # current_amount = input_slots['used_amount']
            # advance_date = input_slots['advance_date']

            mycursor = self.connect.cursor()
            sql = "INSERT INTO "
            sql += self.name_table_user + " (id_conversation) VALUES (%s)"
            val = (id_conversation,)
            mycursor.execute(sql, val)

            self.connect.commit()

            # list_slots = [ x.name for x in self.domain.slots ]
            return response.json({
                "status": 0,
                "msg": "Success",
            })

        # inputSlots
        @custom_webhook.route("/getConversation", methods=["POST"])
        async def get_conversation(request: Request) -> HTTPResponse:
            self.connect.ping(reconnect=True)
            id_conversation = request.json.get("id_conversation")
            if id_conversation is None:
                return response.json({
                    "status": -1,
                    "msg": "Fail",
                    "conversation": None,
                })
            mycursor = self.connect.cursor()
            sql = "SELECT pre_action, timestamp, intent_name, action_name, text_user, text_bot FROM "
            sql += self.name_table_history + " WHERE sender_id like %s"
            mycursor.execute(sql, [id_conversation])
            myresult = mycursor.fetchall()
            result = []
            for x in myresult:
                bot_json = json.loads(x[5])
                if x[3] == "action_start" and x[2] == "null_intent":
                    result = []
                    result.append({
                        "pre_action": "START",
                        "timestamp": x[1],
                        "intent_name": x[2],
                        "action_name": x[3],
                        "text_user": x[4],
                        "text_bot": bot_json['text'],
                        "text_tts_bot": bot_json['text_tts'],
                        "status_bot": bot_json['status']
                    })
                else:
                    result.append({
                        "pre_action": x[0],
                        "timestamp": x[1],
                        "intent_name": x[2],
                        "action_name": x[3],
                        "text_user": x[4],
                        "text_bot": bot_json['text'],
                        "text_tts_bot": bot_json['text_tts'],
                        "status_bot": bot_json['status']
                    })
            return response.json({
                "status": 0,
                "msg": "Success",
                "conversation": result,
            })

        @custom_webhook.route("/notuse", methods=["POST"])
        async def receive(request: Request) -> HTTPResponse:
            sender_id = await self._extract_sender(request)
            text = self._extract_message(request)
            should_use_stream = rasa.utils.endpoints.bool_arg(
                request, "stream", default=False
            )
            input_channel = self._extract_input_channel(request)
            metadata = self.get_metadata(request)

            if should_use_stream:
                return response.stream(
                    self.stream_response(
                        on_new_message, text, sender_id, input_channel, metadata
                    ),
                    content_type="text/event-stream",
                )
            else:
                collector = CollectingOutputChannel()
                # noinspection PyBroadException
                try:
                    await on_new_message(
                        UserMessage(
                            text,
                            collector,
                            sender_id,
                            input_channel=input_channel,
                            metadata=metadata,
                        )
                    )
                except CancelledError:
                    logger.error(
                        "Message handling timed out for "
                        "user message '{}'.".format(text)
                    )
                except Exception:
                    logger.exception(
                        "An exception occured while handling "
                        "user message '{}'.".format(text)
                    )
                return response.json(collector.messages)

        return custom_webhook
