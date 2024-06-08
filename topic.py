from storage import types
from telebot import types as tel_types
# from context import tx


class Topic:
    def __init__(self, storage: types.TopicStorage):
        self.storage = storage

    def get_messages(self, topic_id: int) -> list[types.Message]:
        return self.storage.get_messages(topic_id)

    def append_message(self, topic_id: int, message: types.Message):
        self.storage.append_message(topic_id, message)

    def get_topic(self, topic_id: str) -> types.Topic:
        return self.storage.get_topic(topic_id)

    def list_topics(self, uid: int, chat_id: int) -> list[types.Topic]:
        return self.storage.list_topics(uid, chat_id)

    def create_topic(self):
        pass
