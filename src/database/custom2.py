from rasa.core.tracker_store import TrackerStore
import contextlib
import warnings
import json
import logging
import os
import pickle
import typing
from datetime import datetime, timezone
from typing import Iterator, Optional, Text, Iterable, Union, Dict, Callable

import itertools
from boto3.dynamodb.conditions import Key

# noinspection PyPep8Naming
from time import sleep
import time

from rasa.core.actions.action import ACTION_LISTEN_NAME
from rasa.core.brokers.event_channel import EventChannel
from rasa.core.conversation import Dialogue
from rasa.core.domain import Domain
from rasa.core.trackers import ActionExecuted, DialogueStateTracker, EventVerbosity
from rasa.core.utils import replace_floats_with_decimals
from rasa.utils.common import class_from_module_path
from rasa.utils.endpoints import EndpointConfig
import mysql.connector as mysql_db
import time

if typing.TYPE_CHECKING:
    from sqlalchemy.engine.url import URL
    from sqlalchemy.engine.base import Engine
    from sqlalchemy.orm import Session
    import boto3

logger = logging.getLogger(__name__)

class SQLTrackerStoreC2(TrackerStore):
    """Store which can save and retrieve trackers from an SQL database."""

    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class SQLEvent(Base):
        """Represents an event in the SQL Tracker Store"""

        from sqlalchemy import Column, Integer, String, Float, Text

        __tablename__ = "events"

        id = Column(Integer, primary_key=True)
        sender_id = Column(String(255), nullable=False, index=True)
        type_name = Column(String(255), nullable=False)
        timestamp = Column(Float)
        intent_name = Column(String(255))
        action_name = Column(String(255))
        data = Column(Text)

    def __init__(
        self,
        domain: Optional[Domain] = None,
        dialect: Text = "sqlite",
        host: Optional[Text] = None,
        port: Optional[int] = None,
        db: Text = "rasa.db",
        username: Text = None,
        password: Text = None,
        event_broker: Optional[EventChannel] = None,
        login_db: Optional[Text] = None,
        query: Optional[Dict] = None,
        name_table: Text = None,
    ) -> None:
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        import sqlalchemy.exc

        self.connect = mysql_db.connect(host = host, username = username,
                            password= password,
                            db = db, 
                            port = port)

        self.pre_action_ = "START"
        self.name_table = name_table

        engine_url = self.get_db_url(
            dialect, host, port, db, username, password, login_db, query
        )
        logger.debug(
            "Attempting to connect to database via '{}'.".format(repr(engine_url))
        )

        # Database might take a while to come up
        while True:
            try:
                # pool_size and max_overflow can be set to control the number of
                # connections that are kept in the connection pool. Not available
                # for SQLite, and only  tested for postgresql. See
                # https://docs.sqlalchemy.org/en/13/core/pooling.html#sqlalchemy.pool.QueuePool
                if dialect == "postgresql":
                    self.engine = create_engine(
                        engine_url,
                        pool_size=int(os.environ.get("SQL_POOL_SIZE", "50")),
                        max_overflow=int(os.environ.get("SQL_MAX_OVERFLOW", "100")),
                    )
                else:
                    self.engine = create_engine(engine_url)

                # if `login_db` has been provided, use current channel with
                # that database to create working database `db`
                if login_db:
                    self._create_database_and_update_engine(db, engine_url)

                try:
                    self.Base.metadata.create_all(self.engine)
                except (
                    sqlalchemy.exc.OperationalError,
                    sqlalchemy.exc.ProgrammingError,
                ) as e:
                    # Several Rasa services started in parallel may attempt to
                    # create tables at the same time. That is okay so long as
                    # the first services finishes the table creation.
                    logger.error(f"Could not create tables: {e}")

                self.sessionmaker = sessionmaker(bind=self.engine)
                break
            except (
                sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.IntegrityError,
            ) as error:

                logger.warning(error)
                sleep(5)

        logger.debug(f"Connection to SQL database '{db}' successful.")

        super().__init__(domain, event_broker)

    def insert_database(self, sender_id, pre_action, timestamp, intent_name, action_name,
                        text_user, text_bot):
        self.connect.ping(reconnect = True)
        mycursor = self.connect.cursor()

        sql = "INSERT INTO "
        sql += self.name_table + " (sender_id, pre_action, timestamp, intent_name, action_name,"
        sql += " text_user, text_bot) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (sender_id, pre_action, timestamp, intent_name, action_name, 
                        text_user, text_bot)
        mycursor.execute(sql, val)

        self.connect.commit()


    @staticmethod
    def get_db_url(
        dialect: Text = "sqlite",
        host: Optional[Text] = None,
        port: Optional[int] = None,
        db: Text = "rasa.db",
        username: Text = None,
        password: Text = None,
        login_db: Optional[Text] = None,
        query: Optional[Dict] = None,
    ) -> Union[Text, "URL"]:
        """Builds an SQLAlchemy `URL` object representing the parameters needed
        to connect to an SQL database.

        Args:
            dialect: SQL database type.
            host: Database network host.
            port: Database network port.
            db: Database name.
            username: User name to use when connecting to the database.
            password: Password for database user.
            login_db: Alternative database name to which initially connect, and create
                the database specified by `db` (PostgreSQL only).
            query: Dictionary of options to be passed to the dialect and/or the
                DBAPI upon connect.

        Returns:
            URL ready to be used with an SQLAlchemy `Engine` object.

        """
        from urllib.parse import urlsplit
        from sqlalchemy.engine.url import URL

        # Users might specify a url in the host
        parsed = urlsplit(host or "")
        if parsed.scheme:
            return host

        if host:
            # add fake scheme to properly parse components
            parsed = urlsplit("schema://" + host)

            # users might include the port in the url
            port = parsed.port or port
            host = parsed.hostname or host

        return URL(
            dialect,
            username,
            password,
            host,
            port,
            database=login_db if login_db else db,
            query=query,
        )

    def _create_database_and_update_engine(self, db: Text, engine_url: "URL"):
        """Create databse `db` and update engine to reflect the updated `engine_url`."""

        from sqlalchemy import create_engine

        self._create_database(self.engine, db)
        engine_url.database = db
        self.engine = create_engine(engine_url)

    @staticmethod
    def _create_database(engine: "Engine", db: Text):
        """Create database `db` on `engine` if it does not exist."""

        import psycopg2

        conn = engine.connect()

        cursor = conn.connection.cursor()
        cursor.execute("COMMIT")
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db}'")
        exists = cursor.fetchone()
        if not exists:
            try:
                cursor.execute(f"CREATE DATABASE {db}")
            except psycopg2.IntegrityError as e:
                logger.error(f"Could not create database '{db}': {e}")

        cursor.close()
        conn.close()

    @contextlib.contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.sessionmaker()
        try:
            yield session
        finally:
            session.close()

    def keys(self) -> Iterable[Text]:
        """Returns sender_ids of the SQLTrackerStore"""
        with self.session_scope() as session:
            sender_ids = session.query(self.SQLEvent.sender_id).distinct().all()
            return [sender_id for (sender_id,) in sender_ids]

    def retrieve(self, sender_id: Text) -> Optional[DialogueStateTracker]:
        """Create a tracker from all previously stored events."""

        with self.session_scope() as session:
            query = session.query(self.SQLEvent)
            result = (
                query.filter_by(sender_id=sender_id)
                .order_by(self.SQLEvent.timestamp)
                .all()
            )

            events = [json.loads(event.data) for event in result]

            if self.domain and len(events) > 0:
                logger.debug(f"Recreating tracker from sender id '{sender_id}'")
                return DialogueStateTracker.from_dict(
                    sender_id, events, self.domain.slots
                )
            else:
                logger.debug(
                    "Can't retrieve tracker matching "
                    "sender id '{}' from SQL storage. "
                    "Returning `None` instead.".format(sender_id)
                )
                return None

    def save(self, tracker: DialogueStateTracker) -> None:
        """Update database with events from the current conversation."""

        if self.event_broker:
            self.stream_events(tracker)

        with self.session_scope() as session:
            # only store recent events
            events = self._additional_events(session, tracker)

            intent_real = None
            action_real = None
            text_user_ = None
            text_bot_ = None

            for event in events:
                data = event.as_dict()

                intent = data.get("parse_data", {}).get("intent", {}).get("name")
                action = data.get("name")
                timestamp = data.get("timestamp")

                if data.get('event') == "user":
                    text_user_ = data.get("text")
                if data.get('event') == "bot":
                    text_bot_ = data.get("text")
                intent = data.get("parse_data", {}).get("intent", {}).get("name")
                action = data.get("name")
                if action!= None and action!="action_listen":
                    action_real = action
                # timestamp = data.get("timestamp")
                if intent!=None:
                    intent_real = intent

                session.add(
                    self.SQLEvent(
                        sender_id=tracker.sender_id,
                        type_name="abc",
                        timestamp=timestamp,
                        intent_name=intent,
                        action_name=action,
                        data=json.dumps(data),
                    )
                )
            times_ = time.time()
            if intent_real != None and action_real != None and text_bot_ != None and text_user_!=None:
                # insert data into database mysql
                self.insert_database(tracker.sender_id, self.pre_action_, times_, intent_real, action_real,
                            text_user_, text_bot_)
                self.pre_action_ = action_real
            session.commit()

        logger.debug(
            "Tracker with sender_id '{}' "
            "stored to database".format(tracker.sender_id)
        )

    def _additional_events(
        self, session: "Session", tracker: DialogueStateTracker
    ) -> Iterator:
        """Return events from the tracker which aren't currently stored."""

        n_events = (
            session.query(self.SQLEvent.sender_id)
            .filter_by(sender_id=tracker.sender_id)
            .count()
            or 0
        )

        return itertools.islice(tracker.events, n_events, len(tracker.events))
