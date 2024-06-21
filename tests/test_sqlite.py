import unittest
import asyncio
import time
import os

from unittest import IsolatedAsyncioTestCase
from pathlib import Path

from catgpt.storage.sqlite3_session_storage import (
    Sqlite3Datasource,
    Sqlite3TopicStorage,
    Sqlite3ProfileStorage,
)
import catgpt.storage as storage
from catgpt.storage import types
from catgpt.topic import Topic
from catgpt.user_profile import UserProfile


class TestService(IsolatedAsyncioTestCase):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.internal_tid = 0

    def setUp(self):
        db_file = "file::memory:?cache=shared"
        if os.path.exists(db_file):
            os.remove(db_file)

        schema_file = (
            Path(__file__)
            .parent.parent.joinpath("src/catgpt/data")
            .joinpath("session_schema.sql")
        )
        datasource = Sqlite3Datasource(db_file, schema_file)
        storage.datasource = datasource

        topic_storage = Sqlite3TopicStorage()
        profile_storage = Sqlite3ProfileStorage()

        self.topic = Topic(topic_storage)
        self.profile = UserProfile(profile_storage, Path("presets.json"))

        async def init_data():
            messages = [
                types.Message(
                    role="user",
                    content="Hi.",
                    message_id=1,
                    chat_id=1,
                    topic_id=1,
                    ts=int(time.time()),
                    message_type=0,
                ),
                types.Message(
                    role="assistant",
                    content="Hi. How can I assist you today?",
                    message_id=1,
                    chat_id=1,
                    topic_id=1,
                    ts=int(time.time() + 1),
                    message_type=0,
                ),
            ]

            record = await self.topic.new_topic(
                title="the topic for test",
                chat_id=1,
                user_id=3,
                messages=messages,
                generate_title=True,
                thread_id=0,
            )

            self.assertTrue(record.tid > 0)
            self.internal_tid = record.tid
            data_in_db: types.Topic = await self.topic.get_topic(
                record.tid, fetch_messages=True
            )
            self.assertTrue(
                data_in_db.tid == record.tid and len(data_in_db.messages) == 2
            )

        asyncio.run(init_data())

    async def test_new_topic(self):
        record = await self.topic.new_topic(
            title="test", chat_id=1, user_id=3, messages=[], generate_title=True
        )

        self.assertTrue(record.tid > 0)

    async def test_get_messages(self):
        messages = await self.topic.get_messages([self.internal_tid])
        self.assertTrue(len(messages) == 2)

    async def test_list_topics(self):
        topics = await self.topic.list_topics(3, 1, 0)
        self.assertTrue(len(topics) >= 1)

    async def test_clear_topic(self):
        data = await self.topic.get_topic(self.internal_tid)
        self.assertTrue(data)

        await self.topic.clear_topic(data)
        data: types.Topic = await self.topic.get_topic(self.internal_tid)

        self.assertTrue(data and data.title == "new topic" and data.generate_title > 0)


if __name__ == "__main__":
    unittest.main()
