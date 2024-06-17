from telebot.async_telebot import AsyncTeleBot, asyncio_helper

from pathlib import Path

from .user_profile import UserProfile
from .topic import Topic
from . import storage

import json
import random


class Endpoint:

    def __init__(
            self,
            name: str,
            api_url: str,
            secret_key: str,
            models: list[str],
            provider: str = "openai",
            default_model: str = None,
            default_endpoint: bool = False,
            generate_title: bool = True,
    ):
        assert len(name) > 0, "endpoint name can't be empty"
        assert len(api_url) > 0, "api url can't be empty"
        assert len(secret_key) > 0, "secret key can't be empty"
        assert len(models) > 0, "models can't be empty"

        self.name = name
        self.api_url = api_url
        self.secret_key = secret_key
        self.models = models
        self.generate_title = generate_title
        self.default_endpoint = default_endpoint
        self.provider = provider
        self.default_model = default_model
        if not default_model:
            self.default_model = models[0]

    def __str__(self):
        return f"""
        Endpoint(
            name={self.name}, 
            api_url={self.api_url}, 
            default_model={self.default_model}, 
            models={self.models}
        )"""


class Configuration:

    def __init__(self):
        self.access_key: str = ""
        self.proxy_url: str = ""
        self.share_info = None
        self.endpoints: [Endpoint] = []

    def get_endpoints(self) -> [Endpoint]:
        return self.endpoints

    def get_default_endpoint(self) -> Endpoint:
        for endpoint in self.get_endpoints():
            if endpoint.default_endpoint:
                return endpoint

        return self.get_endpoints()[0]

    def get_endpoint(self, endpoint_name: str) -> Endpoint | None:
        for endpoint in self.get_endpoints():
            if endpoint.name == endpoint_name:
                return endpoint

        return None

    def get_title_endpoint(self) -> [Endpoint]:
        endpoints = self.get_endpoints()

        endpoints = [endpoint for endpoint in endpoints if endpoint.generate_title]

        return random.choices(endpoints)

    def get_models(self) -> list[str]:
        endpoints = self.get_endpoints()
        models = set()
        for endpoint in endpoints:
            models.update(endpoint.models)

        return sorted(models)


config = Configuration()

profiles: UserProfile | None = None
topic: Topic | None = None
bot: AsyncTeleBot | None = None
bot_name = None


async def init_configuration(options):
    def load_config():
        with open(options.config, 'r') as f:
            return json.load(f)

    c = load_config()
    assert 'tg_token' in c, "tg_token is required"
    assert 'access_key' in c, "access_key is required"
    assert 'endpoints' in c, "endpoints is required"

    config.access_key = c['access_key']
    config.proxy_url = c.get('proxy', None)
    config.share_info = c.get("share", None)

    endpoints = c.get('endpoints', [])
    assert len(endpoints) > 0, "endpoints is required"

    list_endpoints = []
    for endpoint in endpoints:
        list_endpoints.append(Endpoint(**endpoint))

    config.endpoints = list_endpoints

    global bot
    bot = AsyncTeleBot(
        token=c['tg_token'],
        disable_web_page_preview=True,
    )


async def init_datasource(options):
    global topic
    global profiles
    from .storage.sqlite3_session_storage import Sqlite3Datasource, Sqlite3TopicStorage, Sqlite3ProfileStorage

    schema_file = Path(__file__).parent.joinpath("data").joinpath("session_schema.sql")

    datasource = Sqlite3Datasource("data.db", schema_file)
    storage.datasource = datasource
    topic_storage = Sqlite3TopicStorage()
    topic = Topic(topic_storage)

    profile_storage = Sqlite3ProfileStorage()
    f_preset = Path(options.preset or "presets.json")

    profiles = UserProfile(profile_storage, f_preset)


async def init(options):
    assert options.config is not None, "Config file is required"
    await init_configuration(options)
    await init_datasource(options)

    if config.proxy_url is not None:
        asyncio_helper.proxy = config.proxy_url


async def get_bot_name():
    global bot_name
    if bot_name is None:
        bot_name = "@" + (await bot.get_me()).username
    return bot_name
