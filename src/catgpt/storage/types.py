from abc import ABC, abstractmethod


class Message:
    def __init__(
        self, role, content, message_id, chat_id, topic_id, ts, message_type=0
    ):
        self.role = role
        self.content = content
        self.message_id = message_id
        self.chat_id = chat_id
        self.ts = ts
        self.topic_id = topic_id
        self.message_type = message_type
        self.media_url = None

    def __repr__(self):
        return (
            f"Message(role={self.role}, content={self.content}, message_id={self.message_id}, "
            f"chat_id={self.chat_id}, ts={self.ts}, topic_id={self.topic_id}), message_type={self.message_type}"
        )


class MessageHolder:
    def __init__(
        self, content, message_id, user_id, chat_id, topic_id, reply_id, message_type=0
    ):
        self.content = content
        self.message_id = message_id
        self.user_id = user_id
        self.chat_id = chat_id
        self.topic_id = topic_id
        self.reply_id = reply_id
        self.message_type = message_type
        self.media_url = None

    def __repr__(self):
        return (
            f"MessageHolder(content={self.content}, message_id={self.message_id}, "
            f"user_id={self.user_id}, chat_id={self.chat_id}, topic_id={self.topic_id}), message_type={self.message_type}"
        )


class Topic:
    def __init__(
        self,
        tid: int,
        label: str,
        chat_id: int,
        user_id: int,
        title: str,
        generate_title: bool,
        thread_id: int,
    ):
        self.tid = tid
        self.title = title
        self.label = label
        self.chat_id = chat_id
        self.user_id = user_id
        self.generate_title = generate_title
        self.thread_id = thread_id
        self.messages: list[Message] = []

    def __repr__(self):
        return (
            f"Topic(id={self.tid}, title={self.title}, label={self.label}, chat_id={self.chat_id}, "
            f"user_id={self.user_id}, messages={self.messages}), thread_id={self.thread_id}, "
        )


class Profile:
    def __init__(
        self,
        uid: int,
        model: str,
        endpoint: str,
        prompt: str,
        chat_type: int,
        chat_id: int,
        thread_id: int,
        topic_id: int,
    ):
        self.uid = uid
        self.model = model
        self.endpoint = endpoint
        self.prompt = prompt
        self.chat_type = chat_type
        self.chat_id = chat_id
        self.thread_id = thread_id
        self.topic_id = topic_id

    def get_key(self):
        return f"{self.uid}-{self.chat_id}-{self.thread_id}"

    def __repr__(self):
        return (
            f"Profile(uid={self.uid}, model={self.model}, endpoint={self.endpoint}, prompt={self.prompt}, "
            f"chat_type={self.chat_type}, chat_id={self.chat_id}, thread_id={self.thread_id})"
        )


class User:
    def __init__(self, uid: int, blocked: int):
        self.uid = uid
        self.blocked = blocked


class GroupInfo:
    def __init__(self, chat_id: int, respond_message: int):
        self.chat_id = chat_id
        self.respond_message = respond_message


class TopicStorage(ABC):
    @abstractmethod
    async def append_message(self, topic_id: int, message: [Message]):
        pass

    @abstractmethod
    async def get_messages(self, topic_id: list[int]) -> list[Message]:
        pass

    @abstractmethod
    async def remove_messages(self, topic_id: int, message_ids: list[int]):
        pass

    @abstractmethod
    async def remove_message_by_topic(self, topic_id: int):
        pass

    @abstractmethod
    async def get_topic(self, topic_id: int) -> Topic:
        pass

    @abstractmethod
    async def list_topics(self, uid: int, chat_id: int, thread_id: int) -> list[Topic]:
        pass

    @abstractmethod
    async def delete_topic(self, topic_id: int):
        pass

    @abstractmethod
    async def create_topic(self, topic: Topic):
        pass

    @abstractmethod
    async def update_topic(self, topic: Topic):
        pass

    async def get_message_holder(
        self, user_id: int, chat_id: int
    ) -> [MessageHolder | None]:
        pass

    async def update_message_holder(self, message: MessageHolder):
        pass

    async def save_message_holder(self, message: MessageHolder):
        pass


class ProfileStorage:
    @abstractmethod
    async def create_profile(self, profile: Profile) -> int:
        pass

    @abstractmethod
    async def get_profile(
        self, uid: int, chat_id: int, thread_id: int
    ) -> [Profile | None]:
        pass

    @abstractmethod
    async def update(self, uid: int, chat_id: int, thread_id: int, profile: Profile):
        pass


class UserStorage:
    @abstractmethod
    async def get_user(self, uid: int) -> [User | None]:
        pass

    @abstractmethod
    async def create_user(self, user: User) -> int:
        pass


class GroupInfoStorage:
    @abstractmethod
    async def get_group_info(self, chat_id: int) -> [GroupInfo | None]:
        pass

    async def create_group_info(self, group_info: GroupInfo) -> int:
        pass

    async def update_group_info(self, chat_id: int, respond_message: int):
        pass
