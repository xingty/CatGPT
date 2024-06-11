from abc import ABC, abstractmethod


class Message:
    def __init__(self, role, content, message_id, chat_id, topic_id, ts):
        self.role = role
        self.content = content
        self.message_id = message_id
        self.chat_id = chat_id
        self.ts = ts
        self.topic_id = topic_id

    def __repr__(self):
        return f"Message(role={self.role}, content={self.content}, message_id={self.message_id}, " \
               f"chat_id={self.chat_id}, ts={self.ts}, topic_id={self.topic_id})"


def adapt_message(message):
    return message.role, message.content, message.message_id, message.chat_id, message.ts, message.topic_id


def adapter_topic(t):
    return t.id, t.label, t.chat_id, t.user_id, t.title, t.generate_title


class Topic:
    def __init__(
            self,
            tid: int,
            title: str,
            label: str,
            chat_id: int,
            user_id: int,
            generate_title: bool
    ):
        self.tid = tid
        self.title = title
        self.label = label
        self.chat_id = chat_id
        self.user_id = user_id
        self.generate_title = generate_title
        self.messages = []

    def __repr__(self):
        return f"Topic(id={self.tid}, title={self.title}, label={self.label}, chat_id={self.chat_id}, " \
               f"user_id={self.user_id}, messages={self.messages})"


class TopicStorage(ABC):
    @abstractmethod
    async def append_message(self, topic_id: int, message: [Message]):
        pass

    @abstractmethod
    async def get_messages(self, topic_id: int) -> list[Message]:
        pass

    @abstractmethod
    async def remove_messages(self, topic_id: int, message_id: int):
        pass

    @abstractmethod
    async def remove_message_by_topic(self, topic_id: int):
        pass

    @abstractmethod
    async def get_topic(self, topic_id: int) -> Topic:
        pass

    @abstractmethod
    async def list_topics(self, uid: int, chat_id: int) -> list[Topic]:
        pass

    @abstractmethod
    async def delete_topic(self, topic_id: int):
        pass

    @abstractmethod
    async def create_topic(self, topic: Topic):
        pass
