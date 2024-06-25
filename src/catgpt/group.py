from .storage.types import GroupInfoStorage, GroupInfo


class GroupConfig:
    def __init__(self, storage: GroupInfoStorage, respond_messages: int):
        self.storage = storage
        self.respond_messages = respond_messages
        self.memory = {}

    async def is_respond_group_message(self, chat_id: int):
        key = str(chat_id)
        if key in self.memory:
            return self.memory[key]

        info = await self.storage.get_group_info(chat_id)
        if not info:
            await self.storage.create_group_info(
                GroupInfo(chat_id, self.respond_messages)
            )

        self.memory[key] = self.respond_messages

        return self.respond_messages

    async def update_respond_messages(self, chat_id: int, respond_messages: int):
        await self.storage.update_group_info(chat_id, respond_messages)
        self.memory[str(chat_id)] = respond_messages
