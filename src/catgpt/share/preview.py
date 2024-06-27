from . import get_provider_by_type
from ..types import Preview


class PagePreview:
    def __init__(self, profiles):
        self.provider = get_provider_by_type(Preview.TELEGRAPH)
        self.profiles = profiles

    async def preview_md_text(self, profile, title, content):
        token = self.provider.get_token()
        if profile.preview_url and profile.preview_token == token:
            url = await self.provider.update_text(profile.preview_url, title, content)
            return url

        result = await self.create_preview_page(content)
        if "url" in result and "path" in result:
            profile.preview_url = result["path"]
            profile.preview_token = token
            await self.profiles.update(
                profile.uid, profile.chat_id, profile.thread_id, profile
            )

            return result["url"]

    async def preview_chat(self, aid, title, content):
        return await self.provider.share_text(aid, title, content)

    async def create_preview_page(self, content):
        import uuid

        article_id = str(uuid.uuid4())
        return await self.provider.create_page(article_id, content)
