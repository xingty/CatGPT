import asyncio
import sqlite3
import os

from pathlib import Path

from ..storage import Datasource, tx, Topic
from ..storage import types

VERSION = [
    {
        "version": "0.1.1",
        "version_code": 2401010501,
        "sql_list": [""],
    }
]


def migrate(connection):
    # execute sql to migrate to the specified version
    pass


class ConnectionProxy:
    def __init__(self, connection, datasource):
        self._connection = connection
        self.datasource = datasource

    def __getattr__(self, name):
        attr = getattr(self._connection, name)
        if callable(attr):

            def wrapper(*args, **kwargs):
                result = None
                try:
                    result = attr(*args, **kwargs)
                finally:
                    if name == "close":
                        self.datasource.release()
                return result

            return wrapper
        else:
            return attr


class Sqlite3Datasource(Datasource):
    def __init__(self, db_file: str, schema_file: Path):
        self.db_file = db_file
        self.pool = asyncio.Queue(1)

        if not os.path.exists(self.db_file):
            conn = sqlite3.connect(self.db_file)
            schema_commands = schema_file.read_text(encoding="utf-8")
            conn.executescript(schema_commands)
            conn.execute("pragma journal_mode=wal;")
            conn.close()

        self.pool.put_nowait(sqlite3.connect(self.db_file))

    async def get_write_conn(self):
        connection = await self.pool.get()
        return ConnectionProxy(connection, self)

    async def get_read_conn(self):
        return sqlite3.connect(self.db_file)

    def release(self):
        if self.pool.empty():
            self.pool.put_nowait(sqlite3.connect(self.db_file))


class Sqlite3TopicStorage(types.TopicStorage, tx.Transactional):

    @staticmethod
    def _decode_message_content(message):
        if message.message_type == 1:
            content = message.content or ""
            segments = content.split(",")
            if len(segments) > 1:
                message.content = segments[1]

            message.media_url = segments[0]

    @staticmethod
    def _encode_message_content(message: types.Message):
        if message.message_type == 1:
            message.content = f"{message.media_url},{message.content}"

    @tx.transactional(tx_type="write")
    async def append_message(self, topic_id: int, message: [types.Message]):
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        tuples = []
        for m in message:
            content = m.content
            if m.message_type == 1:
                content = f"{m.media_url},{content}"

            t = (
                m.role,
                content,
                m.message_id,
                m.chat_id,
                m.ts,
                topic_id,
                m.message_type,
            )
            tuples.append(t)

        sql = """
        insert into message (role, content, message_id, chat_id, ts, topic_id, message_type) values (?,?,?,?,?,?,?)
        """
        conn.executemany(sql, tuples)

    @tx.transactional(tx_type="write")
    async def save_message_holder(self, message: types.MessageHolder):
        transaction = await self.retrieve_transaction()
        conn = transaction.connection

        content = message.content
        if message.message_type == 1:
            content = f"{message.media_url},{content}"

        tuples = (
            content,
            message.message_id,
            message.topic_id,
            message.message_type,
            message.user_id,
            message.chat_id,
        )
        sql = "insert into message_holder (content, message_id, user_id, chat_id, topic_id, reply_id, message_type) values (?,?,?,?,?,?,?)"
        conn.execute(sql, tuples)

    @tx.transactional(tx_type="read")
    async def get_message_holder(
        self, uid: int, chat_id: int
    ) -> [types.MessageHolder | None]:
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        t = (uid, chat_id)
        sql = "select * from message_holder where user_id = ? and chat_id = ?"
        row = conn.execute(sql, t).fetchone()
        if not row:
            return None

        holder = types.MessageHolder(*row)
        if holder.message_type == 1:
            self._decode_message_content(holder)

        return holder

    @tx.transactional(tx_type="write")
    async def update_message_holder(self, message: types.MessageHolder):
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        content = message.content
        if message.message_type == 1:
            content = f"{message.media_url},{content}"

        tuples = (
            content,
            message.message_id,
            message.topic_id,
            message.message_type,
            message.user_id,
            message.chat_id,
        )

        sql = "update message_holder set content = ?, message_id = ?, topic_id = ?, message_type = ? where user_id = ? and chat_id = ?"

        conn.execute(sql, tuples)

    @tx.transactional(tx_type="read")
    async def get_messages(self, topic_ids: list[int]) -> list[types.Message]:
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        placeholders = ",".join(["?"] * len(topic_ids))

        records = conn.execute(
            f"select * from message where topic_id IN ({placeholders})", topic_ids
        ).fetchall()
        if not records:
            return []

        messages = []
        for r in records:
            msg = types.Message(*r)
            self._decode_message_content(msg)
            messages.append(msg)

        return messages

    @tx.transactional(tx_type="read")
    async def get_topic(self, topic_id: int) -> [types.Topic | None]:
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        row = conn.execute("select * from topic where tid = ?", (topic_id,)).fetchone()
        if not row:
            return None

        return types.Topic(*row)

    @tx.transactional(tx_type="read")
    async def list_topics(
        self, uid: int, chat_id: int, thread_id: int
    ) -> list[types.Topic]:
        t = await self.retrieve_transaction()
        sql = "select * from topic where user_id = ? and chat_id = ?"
        params = [uid, chat_id]
        if thread_id:
            sql += " and thread_id = ?"
            params.append(thread_id)

        records = t.connection.execute(sql, params).fetchall()
        if not records:
            return []

        return [types.Topic(*r) for r in records]

    @tx.transactional(tx_type="write")
    async def delete_topic(self, topic_id: int):
        t = await self.retrieve_transaction()
        t.connection.execute("delete from topic where tid = ?", (topic_id,))
        # await self.remove_message_by_topic(topic_id)

    @tx.transactional(tx_type="write")
    async def remove_messages(self, topic_id: int, message_ids: list[int]):
        t = await self.retrieve_transaction()
        placeholders = ",".join(["?"] * len(message_ids))
        sql = (
            f"delete from message where topic_id = ? and message_id in ({placeholders})"
        )
        t.connection.execute(sql, (topic_id, *message_ids))

    @tx.transactional(tx_type="write")
    async def remove_message_by_topic(self, topic_id: int):
        t = await self.retrieve_transaction()
        t.connection.execute("delete from message where topic_id = ?", (topic_id,))

    @tx.transactional(tx_type="write")
    async def create_topic(self, topic: Topic) -> int:
        t = await self.retrieve_transaction()
        sql = "insert into topic (label, chat_id, user_id, title, generate_title, thread_id) values (?,?,?,?,?,?)"
        columns = (
            topic.label,
            topic.chat_id,
            topic.user_id,
            topic.title,
            topic.generate_title,
            topic.thread_id or 0,
        )
        cursor = t.connection.execute(sql, columns)
        topic_id = cursor.lastrowid

        return topic_id

    @tx.transactional(tx_type="write")
    async def update_topic(self, topic: Topic):
        t = await self.retrieve_transaction()
        sql = "update topic set label = ?, chat_id = ?, user_id = ?, title = ?, generate_title = ?, thread_id = ? where tid = ?"
        columns = (
            topic.label,
            topic.chat_id,
            topic.user_id,
            topic.title,
            topic.generate_title,
            topic.thread_id or 0,
            topic.tid,
        )
        t.connection.execute(sql, columns)


class Sqlite3UserStorage(types.UserStorage, tx.Transactional):

    @tx.transactional(tx_type="read")
    async def get_user(self, uid: int) -> [types.User | None]:
        t = await self.retrieve_transaction()
        sql = "select * from users where uid = ?"
        row = t.connection.execute(sql, (uid,)).fetchone()
        if not row:
            return None

        return types.User(*row)

    @tx.transactional(tx_type="write")
    async def create_user(self, user: types.User) -> int:
        t = await self.retrieve_transaction()
        sql = "insert into users (uid, blocked) values (?,?)"
        columns = (user.uid, user.blocked)
        cursor = t.connection.execute(sql, columns)
        return cursor.lastrowid


class Sqlite3ProfileStorage(types.ProfileStorage, tx.Transactional):

    @tx.transactional(tx_type="write")
    async def create_profile(self, profile: types.Profile) -> int:
        t = await self.retrieve_transaction()
        sql = "insert into profile (uid, model, endpoint, prompt, chat_type, chat_id, thread_id, topic_id) values "
        columns = (
            profile.uid,
            profile.model,
            profile.endpoint,
            profile.prompt,
            profile.chat_type,
            profile.chat_id,
            profile.thread_id or 0,
            profile.topic_id,
        )
        sql += "(" + ",".join("?" * len(columns)) + ")"

        cursor = t.connection.execute(sql, columns)
        return cursor.lastrowid

    @tx.transactional(tx_type="read")
    async def get_profile(
        self, uid: int, chat_id: int, thread_id: int
    ) -> [types.Profile | None]:
        t = await self.retrieve_transaction()
        sql = "select * from profile where uid = ? and chat_id = ? and thread_id = ?"
        row = t.connection.execute(sql, (uid, chat_id, thread_id or 0)).fetchone()
        if not row:
            return None

        return types.Profile(*row)

    async def get_conversation_id(self, uid: int, chat_type: str) -> int:
        field = "groups"
        if chat_type in ["private", "channel"]:
            field = chat_type

        t = await self.retrieve_transaction()
        sql = f"select {field} from profile where uid = ?"
        row = t.connection.execute(sql, (uid,)).fetchone()
        if not row:
            return 0

        return row[0]

    @tx.transactional(tx_type="write")
    async def update(
        self, uid: int, chat_id: int, thread_id: int, profile: types.Profile
    ):
        t = await self.retrieve_transaction()
        sql = f"update profile set model = ?, endpoint = ?, prompt = ?, topic_id = ? where uid = ? and chat_id = ? and thread_id = ?"
        t.connection.execute(
            sql,
            (
                profile.model,
                profile.endpoint,
                profile.prompt,
                profile.topic_id,
                profile.uid,
                profile.chat_id,
                profile.thread_id or 0,
            ),
        )
