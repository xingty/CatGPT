import asyncio
import sqlite3
import os

from storage import Datasource, types, tx, Topic


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
    def __init__(self, db_file: str, schema_file: str = "assets/session_schema.sql"):
        self.db_file = db_file
        self.pool = asyncio.Queue(1)

        if not os.path.exists(self.db_file):
            conn = sqlite3.connect(self.db_file)
            with open(schema_file) as f:
                schema = f.read()
                conn.executescript(schema)
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
    @tx.transactional(tx_type="write")
    async def append_message(self, topic_id: int, message: [types.Message]):
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        tuples = [tuple(vars(m).values()) for m in message]
        sql = "insert into message (role, content, message_id, chat_id, ts, topic_id) values (?,?,?,?,?,?)"
        conn.executemany(sql, tuples)

    @tx.transactional(tx_type="read")
    async def get_messages(self, topic_ids: list[int]) -> list[types.Message]:
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        placeholders = ','.join(['?'] * len(topic_ids))

        records = conn.execute(f"select * from message where topic_id IN ({placeholders})", topic_ids).fetchall()
        if not records:
            return []

        return [types.Message(*r) for r in records]

    @tx.transactional(tx_type="read")
    async def get_topic(self, topic_id: int) -> [types.Topic | None]:
        transaction = await self.retrieve_transaction()
        conn = transaction.connection
        row = conn.execute("select * from topic where tid = ?", (topic_id,)).fetchone()
        if not row:
            return None

        return types.Topic(*row)

    @tx.transactional(tx_type="read")
    async def list_topics(self, uid: int, chat_id: int) -> list[types.Topic]:
        t = await self.retrieve_transaction()
        sql = "select * from topic where user_id = ? and chat_id = ?"
        records = t.connection.execute(sql, (uid, chat_id)).fetchall()
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
        placeholders = ','.join(['?'] * len(message_ids))
        sql = f"delete from message where topic_id = ? and message_id in ({placeholders})"
        t.connection.execute(sql, (topic_id, *message_ids))

    @tx.transactional(tx_type="write")
    async def remove_message_by_topic(self, topic_id: int):
        t = await self.retrieve_transaction()
        t.connection.execute("delete from message where topic_id = ?", (topic_id,))

    @tx.transactional(tx_type="write")
    async def create_topic(self, topic: Topic) -> int:
        t = await self.retrieve_transaction()
        sql = "insert into topic (label, chat_id, user_id, title, generate_title) values (?,?,?,?,?)"
        columns = (topic.label, topic.chat_id, topic.user_id, topic.title, topic.generate_title)
        cursor = t.connection.execute(sql, columns)
        topic_id = cursor.lastrowid

        if len(topic.messages) > 0:
            for m in topic.messages:
                m.topic_id = topic_id

            await self.append_message(topic_id, topic.messages)

        return topic_id

    @tx.transactional(tx_type="write")
    async def update_topic(self, topic: Topic):
        t = await self.retrieve_transaction()
        sql = "update topic set label = ?, chat_id = ?, user_id = ?, title = ?, generate_title = ? where tid = ?"
        columns = (topic.label, topic.chat_id, topic.user_id, topic.title, topic.generate_title, topic.tid)
        t.connection.execute(sql, columns)


class Sqlite3ProfileStorage(types.ProfileStorage, tx.Transactional):

    @tx.transactional(tx_type="write")
    async def create_profile(self, profile: types.Profile) -> int:
        t = await self.retrieve_transaction()
        sql = "insert into profile (uid, model, endpoint, prompt, private, channel, groups) values (?,?,?,?,?,?,?)"
        columns = (
            profile.uid,
            profile.model,
            profile.endpoint,
            profile.prompt,
            profile.private,
            profile.channel,
            profile.groups,
        )
        cursor = t.connection.execute(sql, columns)
        return cursor.lastrowid

    @tx.transactional(tx_type="read")
    async def get_profile(self, uid: int) -> [types.Profile | None]:
        t = await self.retrieve_transaction()
        sql = "select * from profile where uid = ?"
        row = t.connection.execute(sql, (uid,)).fetchone()
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
    async def update_conversation_id(self, uid: int, chat_type: str, conversation_id: int):
        field = "groups"
        if chat_type in ["private", "channel"]:
            field = chat_type

        t = await self.retrieve_transaction()
        sql = f"update profile set {field} = ? where uid = ?"
        t.connection.execute(sql, (conversation_id, uid))

    @tx.transactional(tx_type="write")
    async def update_prompt(self, uid: int, prompt: str):
        t = await self.retrieve_transaction()
        sql = f"update profile set prompt = ? where uid = ?"
        t.connection.execute(sql, (prompt, uid))

    @tx.transactional(tx_type="write")
    async def update_model(self, uid: int, model: str):
        t = await self.retrieve_transaction()
        sql = f"update profile set model = ? where uid = ?"
        t.connection.execute(sql, (model, uid))

    @tx.transactional(tx_type="write")
    async def update_endpoint(self, uid: int, endpoint: str):
        t = await self.retrieve_transaction()
        sql = f"update profile set endpoint = ? where uid = ?"
        t.connection.execute(sql, (endpoint, uid))

    @tx.transactional(tx_type="write")
    async def update(self, uid: int, profile: types.Profile):
        t = await self.retrieve_transaction()
        sql = f"update profile set model = ?, endpoint = ?, prompt = ?, private = ?, channel = ?, groups = ? where uid = ?"
        t.connection.execute(sql, (
            profile.model,
            profile.endpoint,
            profile.prompt,
            profile.private,
            profile.channel,
            profile.groups,
            uid
        ))
