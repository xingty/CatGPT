import sqlite3
import os

from storage import Datasource, types


class Sqlite3Datasource(Datasource):
    def __init__(self, db_file: str, schema_file: str = "assets/session_schema.sql"):
        self.db_file = db_file
        if not os.path.exists(self.db_file):
            conn = sqlite3.connect(self.db_file)
            with open(schema_file) as f:
                schema = f.read()
                conn.executescript(schema)
            conn.close()

        self.write_connection = sqlite3.connect(db_file)

    async def get_write_conn(self):
        return self.write_connection

    async def get_read_conn(self):
        return sqlite3.connect(self.db_file)


class Sqlite3TopicStorage(types.TopicStorage):
    def append_message(self, topic_id: int, message: [types.Message]):
        pass

    def get_messages(self, topic_id: int) -> list[types.Message]:
        pass

    def get_topic(self, topic_id: str) -> types.Topic:
        pass

    def list_topics(self, uid: int, chat_id: int) -> list[types.Topic]:
        pass