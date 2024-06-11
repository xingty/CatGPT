import asyncio
import sqlite3
import os
import types as t2

from storage import Datasource, types, tx, Topic


class ConnectionProxy:
    def __init__(self, connection, datasource):
        self._connection = connection
        self.datasource = datasource

    def __getattr__(self, name):
        # 通用方法代理
        attr = getattr(self._connection, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
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
    async def get_messages(self, topic_id: int) -> list[types.Message]:
        transaction = await self.retrieve_transaction()
        conn = transaction.connection

        records = conn.execute("select * from message where topic_id = ?", (topic_id,)).fetchall()
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
        await self.remove_message_by_topic(topic_id)

    @tx.transactional(tx_type="write")
    async def remove_messages(self, topic_id: int, message_id: int):
        pass

    @tx.transactional(tx_type="write")
    async def remove_message_by_topic(self, topic_id: int):
        t = await self.retrieve_transaction()
        t.connection.execute("delete from message where topic_id = ?", (topic_id,))

    @tx.transactional(tx_type="write")
    async def create_topic(self, topic: Topic):
        t = await self.retrieve_transaction()
        sql = "insert into topic (label, chat_id, user_id, title, generate_title) values (?,?,?,?,?)"
        columns = (topic.label, topic.chat_id, topic.user_id, topic.title, topic.generate_title)
        cursor = t.connection.execute(sql, columns)
        print(cursor)
        print(cursor.lastrowid)
