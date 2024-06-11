from telebot import types as tel_types

from storage import types, tx


class Topic:
    def __init__(self, storage: types.TopicStorage):
        self.storage = storage

    async def get_messages(self, topic_id: int) -> list[types.Message]:
        return await self.storage.get_messages(topic_id)

    @tx.transactional(tx_type="write")
    async def append_message(self, topic_id: int, message: types.Message):
        await self.storage.append_message(topic_id, message)

    async def get_topic(self, topic_id: str) -> types.Topic:
        return await self.storage.get_topic(topic_id)

    async def list_topics(self, uid: int, chat_id: int) -> list[types.Topic]:
        return await self.storage.list_topics(uid, chat_id)

    async def create_topic(self, topic: types.Topic):
        pass
