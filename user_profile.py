import json

from pathlib import Path

from storage import types

DEFAULT_PROFILE = {
    "prompt": "You are ChatGPT, a large language model trained by OpenAI.\nLatex inline: $x^2$\nLatex block: $$e=mc^2$$",
    "model": None,
    "conversation": {}
}


class UserProfile:
    def __init__(self, storage: types.ProfileStorage):
        self.presets = {}
        self.storage = storage

        self._init_context()

    def _init_context(self):
        file = Path(__file__).parent.joinpath('presets.json')
        presets: [] = json.loads(file.read_text())
        for preset in presets:
            self.presets[preset['role']] = preset

    async def load(self, uid: int) -> types.Profile:
        return await self.storage.get_profile(uid)

    async def create(
            self,
            uid: int,
            model: str,
            endpoint: str,
            prompt: str = "",
            private: int = 0,
            channel: int = 0,
            groups: int = 0,
    ):
        profile = types.Profile(
            uid=uid,
            model=model,
            endpoint=endpoint,
            prompt=prompt,
            private=private,
            channel=channel,
            groups=groups
        )

        await self.storage.create_profile(profile)
        return profile

    def get_preset(self, preset_name: str):
        return self.presets.get(preset_name)

    async def update(self, uid: int, profile: types.Profile):
        assert uid > 0, 'invalid uid: ' + str(uid)
        await self.storage.update(uid, profile)

    async def update_model(self, uid: int, model: str):
        assert uid > 0, 'invalid uid: ' + str(uid)
        assert model, 'invalid model: ' + model

        await self.storage.update_model(uid, model)

    async def update_prompt(self, uid: int, prompt: str):
        assert uid > 0, 'invalid uid: ' + str(uid)
        await self.storage.update_prompt(uid, prompt)

    async def get_conversation_id(self, uid: int, chat_type: str) -> int:
        return await self.storage.get_conversation_id(uid, chat_type)

    async def update_conversation_id(self, uid: int, chat_type: str, conversation_id: int):
        assert uid > 0, 'invalid uid: ' + str(uid)
        await self.storage.update_conversation_id(uid, chat_type, conversation_id)

    async def is_enrolled(self, uid: int) -> bool:
        profile = await self.storage.get_profile(uid)
        return profile is not None

    async def enroll(self, uid: int, model: str, endpoint: str):
        await self.create(
            uid=uid,
            model=model,
            endpoint=endpoint,
            prompt="",
            private=0,
            channel=0,
            groups=0
        )

    def get_prompt(self, prompt) -> str:
        prompt = self.presets.get(prompt, {})
        return prompt.get('prompt', '')
