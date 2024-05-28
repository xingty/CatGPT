from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from utils.md2tgmd import escape
from context import profiles, session, config


async def handle_endpoints(message: Message, bot: AsyncTeleBot):
    uid = str(message.from_user.id)
    profile = profiles.load(uid)
    context = f'{message.message_id}:{message.chat.id}:{uid}'
    keyboard = []
    items = []

    for endpoint in config.get_endpoints():
        name = endpoint["name"]
        callback_data = f'{action["name"]}:{name}:{context}'
        if len(items) == 2:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(name, callback_data=callback_data))

    if len(items) > 0:
        keyboard.append(items)

    endpoint_name = profile.get("endpoint", "None")
    text = f'current endpoint: **{endpoint_name}** \nEndpoints:'
    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def do_endpoint_change(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: str, message: Message):
    endpoint = config.get_endpoint(operation)
    if endpoint is None:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=msg_id,
            parse_mode="MarkdownV2",
            text=escape(f'endpoint not found')
        )
        return

    models = endpoint["models"]
    profile = profiles.load(uid)
    profile["endpoint"] = operation
    if profile.get("model") not in models:
        profile["model"] = endpoint.get("default_model")

    profiles.update_all(uid, profile)

    await bot.send_message(
        chat_id=chat_id,
        reply_to_message_id=msg_id,
        parse_mode="MarkdownV2",
        text=escape(f'current endpoint: `{operation}`')
    )


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_endpoints)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])


action = {
    "name": 'endpoints',
    "description": 'list endpoints',
    "handler": do_endpoint_change,
    "delete_after_invoke": True
}
