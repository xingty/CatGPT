from abc import ABC, abstractmethod


class Message:
    def __init__(self, role, content, message_id, chat_id, topic_id, ts):
        self.role = role
        self.content = content
        self.message_id = message_id
        self.chat_id = chat_id
        self.topic_id = topic_id
        self.ts = ts

    def __repr__(self):
        return f"Message(role={self.role}, content={self.content}, message_id={self.message_id}, " \
               f"chat_id={self.chat_id}, ts={self.ts}, topic_id={self.topic_id})"


def adapt_message(message):
    return message.role, message.content, message.message_id, message.chat_id, message.ts, message.topic_id


class Topic:
    def __init__(self, title: str, messages: list[Message]):
        self.title = title
        self.messages = messages


class TopicStorage(ABC):
    @abstractmethod
    def append_message(self, topic_id: int, message: [Message]):
        pass

    @abstractmethod
    def get_messages(self, topic_id: int) -> list[Message]:
        pass

    @abstractmethod
    def get_topic(self, topic_id: str) -> Topic:
        pass

    @abstractmethod
    def list_topics(self, uid: int, chat_id: int) -> list[Topic]:
        pass
