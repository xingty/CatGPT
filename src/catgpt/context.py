from telebot.async_telebot import AsyncTeleBot, asyncio_helper

from pathlib import Path

from .user_profile import UserProfile, Users
from .group import GroupConfig
from .types import Endpoint, Configuration, Preview
from . import share
from .topic import Topic
from . import storage
from .share.preview import PagePreview

import json


config = Configuration()

group_config: GroupConfig | None = None
profiles: UserProfile | None = None
users: Users | None = None
topic: Topic | None = None
bot: AsyncTeleBot | None = None
bot_name = None
page_preview: PagePreview | None = None


async def init_configuration(options):
    def load_config():
        with open(options.config, "r") as f:
            return json.load(f)

    c = load_config()
    assert "tg_token" in c, "tg_token is required"
    assert "access_key" in c, "access_key is required"
    assert "endpoints" in c, "endpoints is required"

    config.access_key = c["access_key"]
    config.proxy_url = c.get("proxy", None)
    config.share_info = c.get("share", None)
    config.respond_group_message = c.get("respond_group_message", False)
    preview_type = c.get("topic_preview_type", Preview.TELEGRAPH.name)
    config.topic_preview = Preview[preview_type.upper()]

    endpoints = c.get("endpoints", [])
    assert len(endpoints) > 0, "endpoints is required"

    list_endpoints = []
    for endpoint in endpoints:
        list_endpoints.append(Endpoint(**endpoint))

    config.endpoints = list_endpoints

    global bot
    bot = AsyncTeleBot(
        token=c["tg_token"],
        disable_web_page_preview=True,
        disable_notification=True,
    )

    await share.init_providers(c.get("share", []), config)


async def init_datasource(options):
    global topic
    global profiles
    global users
    global group_config
    global page_preview
    from .storage.sqlite3_session_storage import (
        Sqlite3Datasource,
        Sqlite3TopicStorage,
        Sqlite3ProfileStorage,
        Sqlite3UserStorage,
        Sqlite3GroupInfoStorage,
    )

    db_file = options.db_file or "data.db"
    schema_file = Path(__file__).parent.joinpath("data").joinpath("session_schema.sql")

    datasource = Sqlite3Datasource(db_file, schema_file)
    storage.datasource = datasource
    topic_storage = Sqlite3TopicStorage()
    topic = Topic(topic_storage)

    profile_storage = Sqlite3ProfileStorage()
    f_preset = Path(options.preset or "presets.json")

    profiles = UserProfile(profile_storage, f_preset)
    user_storage = Sqlite3UserStorage()
    users = Users(user_storage)

    group_storage = Sqlite3GroupInfoStorage()
    group_config = GroupConfig(group_storage, config.respond_group_message)

    page_preview = PagePreview(profiles)


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
