import uuid

from telebot import types as tg_types

from .storage import types, tx


class Topic:
    def __init__(self, storage: types.TopicStorage):
        self.storage = storage

    async def get_messages(self, topic_ids: list[int]) -> list[types.Message]:
        return await self.storage.get_messages(topic_ids)

    async def append_messages(
            self, topic_id: int,
            user_message: tg_types.Message,
            assistant_message: tg_types.Message
    ):
        messages = [
            types.Message(
                role="user",
                content=user_message.text,
                message_id=user_message.message_id,
                chat_id=user_message.chat.id,
                ts=user_message.date,
                topic_id=topic_id
            ),
            types.Message(
                role="assistant",
                content=assistant_message.text,
                message_id=assistant_message.message_id,
                chat_id=assistant_message.chat.id,
                ts=assistant_message.date + 1,
                topic_id=topic_id
            )
        ]

        await self.storage.append_message(topic_id, messages)

    async def remove_messages(self, topic_id: int, message_ids: list[int]):
        assert topic_id > 0, "Invalid topic id"
        assert len(message_ids) > 0, "message ids cannot be empty"

        await self.storage.remove_messages(topic_id, message_ids)

    async def get_topic(self, topic_id: int, fetch_messages: bool = False) -> [types.Topic | None]:
        topic = await self.storage.get_topic(topic_id)
        if topic is None:
            return None

        if fetch_messages:
            messages = await self.get_messages([topic_id])
            topic.messages = messages

        return topic

    async def list_topics(self, uid: int, chat_id: int) -> list[types.Topic]:
        topics = await self.storage.list_topics(uid, chat_id)
        topic_ids = [topic.tid for topic in topics]
        messages = await self.get_messages(topic_ids)

        mapping = {}
        for m in messages:
            if m.topic_id not in mapping:
                mapping[m.topic_id] = []
            mapping[m.topic_id].append(m)

        for topic in topics:
            topic.messages = mapping.get(topic.tid, [])

        return topics

    @tx.transactional(tx_type="write")
    async def create_topic(self, topic: types.Topic) -> types.Topic:
        topic.tid = await self.storage.create_topic(topic)
        if topic.messages:
            for m in topic.messages:
                m.topic_id = topic.tid
            await self.storage.append_message(topic.tid, topic.messages)

        return topic

    async def update_topic(self, topic: types.Topic):
        assert topic.tid > 0, "Topic id must be > 0"
        await self.storage.update_topic(topic)

    async def new_topic(
            self, title: str,
            chat_id: int,
            user_id: int,
            messages: list = None,
            generate_title: bool = True
    ) -> types.Topic:
        label = str(uuid.uuid4()).replace("-", "")

        topic = types.Topic(
            tid=0,
            user_id=user_id,
            chat_id=chat_id,
            title=title,
            generate_title=generate_title,
            label=label
        )
        if messages:
            topic.messages = messages

        return await self.create_topic(topic)

    @tx.transactional(tx_type="write")
    async def clear_topic(self, topic: types.Topic, prompt: types.Message = None):
        assert topic.tid > 0, "Topic id must be > 0"

        await self.storage.remove_message_by_topic(topic.tid)
        if prompt:
            await self.storage.append_message(topic.tid, [prompt])

        topic.generate_title = 1
        topic.title = "new topic"
        topic.label = str(uuid.uuid4()).replace("-", "")
        await self.storage.update_topic(topic)

    @tx.transactional(tx_type="write")
    async def remove_topic(self, topic_id: int):
        assert topic_id > 0, "Topic id must be > 0"

        await self.storage.delete_topic(topic_id)
        await self.storage.remove_message_by_topic(topic_id)
