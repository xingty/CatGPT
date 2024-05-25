from session import Session
from user_profile import UserProfile
from telebot.async_telebot import AsyncTeleBot, asyncio_helper
from pathlib import Path
import json
import random


class Configuration:

    def __init__(self):
        self.access_key = ""
        self.proxy_url = ""
        self.endpoint_file = None
        self.share_info = None

    def get_endpoints(self):
        return json.loads(self.endpoint_file.read_text())

    def get_default_endpoint(self):
        endpoints = self.get_endpoints()
        for e in endpoints:
            if e.get("default_endpoint", False):
                return e

        return endpoints[0]

    def get_endpoint(self, endpoint_name: str):
        for endpoint in self.get_endpoints():
            if endpoint['name'] == endpoint_name:
                return endpoint

        return None

    def get_title_endpoint(self):
        endpoints = self.get_endpoints()
        endpoints = [endpoint for endpoint in endpoints if endpoint.get("generate_title", False)]

        return random.choices(endpoints)

    def get_models(self):
        endpoints = self.get_endpoints()
        models = set()
        for endpoint in endpoints:
            models.update(endpoint['models'])

        return sorted(models)


session = Session()
profiles = UserProfile()
config = Configuration()
bot: AsyncTeleBot | None = None


async def init(options):
    assert options.config is not None, "Config file is required"

    def load_config():
        with open(options.config, 'r') as f:
            return json.load(f)

    c = load_config()
    assert 'tg_token' in c, "tg_token is required"
    assert 'access_key' in c, "access_key is required"
    assert 'endpoint' in c, "endpoint is required"

    config.access_key = c['access_key']
    config.endpoint_file = Path(c['endpoint'])
    config.proxy_url = c.get('proxy', None)
    config.share_info = c.get("share", None)

    global bot
    bot = AsyncTeleBot(
        token=c['tg_token'],
        disable_web_page_preview=True,
    )

    if config.proxy_url is not None:
        asyncio_helper.proxy = config.proxy_url
