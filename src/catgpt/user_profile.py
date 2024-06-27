import json

from pathlib import Path

from .storage import types
from .types import ChatType

DEFAULT_PROFILE = {
    "prompt": "You are ChatGPT, a large language model trained by OpenAI.\nLatex inline: $x^2$\nLatex block: $$e=mc^2$$",
    "model": None,
    "conversation": {},
}

DEFAULT_PRESET = {"role": "System", "prompt": None}


class UserProfile:
    def __init__(self, storage: types.ProfileStorage, preset_file: Path):
        self.presets = {}
        self.storage = storage

        self.memory = {}

        if preset_file.exists():
            presets: [] = json.loads(preset_file.read_text())
            for preset in presets:
                if "role" in preset and "prompt" in preset:
                    self.presets[preset["role"]] = preset

        if len(self.presets) == 0:
            self.presets["System"] = DEFAULT_PRESET

    async def load(self, uid: int, chat_id: int, thread_id: int) -> types.Profile:
        profile = await self.storage.get_profile(uid, chat_id, thread_id)
        return profile

    async def create(
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
        profile = types.Profile(
            uid=uid,
            model=model,
            endpoint=endpoint,
            prompt=prompt,
            chat_type=chat_type,
            chat_id=chat_id,
            thread_id=thread_id,
            topic_id=topic_id,
            preview_url=None,
            preview_token=None,
        )

        await self.storage.create_profile(profile)
        return profile

    def get_preset(self, preset_name: str):
        return self.presets.get(preset_name)

    async def get_profile(
        self, uid: int, chat_id: int, thread_id: int
    ) -> [types.Profile | None]:
        assert uid > 0, "invalid uid: " + str(uid)
        profile = await self.storage.get_profile(uid, chat_id, thread_id)
        if not profile:
            return None

        self.memory[profile.get_key()] = True

        return profile

    async def has_profile(self, uid: int, chat_id: int, thread_id: int) -> bool:
        assert uid > 0, "invalid uid: " + str(uid)
        key = f"{uid}-{chat_id}-{thread_id}"
        if key in self.memory:
            return True

        profile = await self.get_profile(uid, chat_id, thread_id)

        if not profile:
            return False

        self.memory[key] = True
        return True

    async def update(
        self, uid: int, chat_id: int, thread_id: int, profile: types.Profile
    ):
        assert uid > 0, "invalid uid: " + str(uid)
        await self.storage.update(uid, chat_id, thread_id, profile)

    async def update_model(self, uid: int, chat_id: int, thread_id: int, model: str):
        assert uid > 0, "invalid uid: " + str(uid)
        profile = await self.get_profile(uid, chat_id, thread_id)
        profile.model = model
        await self.storage.update(uid, chat_id, thread_id, profile)

    async def update_prompt(self, uid: int, chat_id: int, thread_id: int, prompt: str):
        assert uid > 0, "invalid uid: " + str(uid)
        profile = await self.get_profile(uid, chat_id, thread_id)
        profile.prompt = prompt
        await self.storage.update(uid, chat_id, thread_id, profile)

    async def get_conversation_id(self, uid: int, chat_type: str) -> int:
        return await self.storage.get_conversation_id(uid, chat_type)

    async def update_conversation_id(
        self, uid: int, chat_id: int, thread_id: int, conversation_id: int
    ):
        assert uid > 0, "invalid uid: " + str(uid)
        profile = await self.get_profile(uid, chat_id, thread_id)
        profile.topic_id = conversation_id
        await self.storage.update(uid, chat_id, thread_id, profile)

    def get_prompt(self, prompt) -> str:
        prompt = self.presets.get(prompt, {})
        return prompt.get("prompt", "")


class Users:
    def __init__(self, storage: types.UserStorage):
        self.storage = storage
        self.memory = {}

    async def get_user(self, uid: int) -> types.User | None:
        return await self.storage.get_user(uid)

    async def create_user(self, uid: int, blocked: int = 0):
        user = types.User(uid=uid, blocked=blocked)
        await self.storage.create_user(user)

    async def is_enrolled(self, uid: int) -> bool:
        if uid in self.memory:
            return True

        u = await self.storage.get_user(uid)
        if u:
            self.memory[uid] = True
            return True

        return False
