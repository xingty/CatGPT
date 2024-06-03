from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from utils.md2tgmd import escape
from context import profiles, session, config

SHORT_NAME = {
    "gpt4": "gpt-4",
    "gpt4_32k": "gpt-4-32k",
    "gpt4_16k": "gpt-4-16k",
    "0314": "gpt-4-0314",
    "0613": "gpt-4-0613",
    "1106": "gpt-4-1106-preview",
    "0125": "gpt-4-0125-preview",
    "0409": "gpt-4-turbo-2024-04-09",
    "gpt4o": "gpt-4o",
}


async def handle_models(message: Message, bot: AsyncTeleBot):
    uid = str(message.from_user.id)
    profile = profiles.load(uid)
    endpoint = config.get_endpoint(profile.get("endpoint", "None"))
    text = message.text.replace("/models", "").strip()
    models = endpoint.get("models", [])

    # fast switch
    if len(text) > 0:
        if text in models:
            await do_model_change(bot, text, message.message_id, message.chat.id, uid, message)
            return
        elif SHORT_NAME[text] in models:
            await do_model_change(bot, SHORT_NAME[text], message.message_id, message.chat.id, uid, message)
            return

    context = f'{message.message_id}:{message.chat.id}:{uid}'
    keyboard = []
    items = []

    for model in endpoint.get("models", []):
        callback_data = f'{action["name"]}:{model}:{context}'
        if len(items) == 2:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(model, callback_data=callback_data))

    if len(items) > 0:
        keyboard.append(items)

    text = f'current endpoint: `{profile.get("endpoint", "None")}`\ncurrent model: `{profile.get("model", "None")}`\n'
    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(text),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def do_model_change(bot: AsyncTeleBot, operation: str, msg_id: int, chat_id: int, uid: str, message: Message):
    profile = profiles.load(uid)
    profile["model"] = operation
    profiles.update_all(uid, profile)

    endpoint = config.get_endpoint(profile.get("endpoint", "None"))
    if operation not in endpoint.get("models", []):
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=msg_id,
            parse_mode="MarkdownV2",
            text=escape(f'current endpoint does not support the model `{operation}`')
        )
        return

    # await bot.delete_message(chat_id, msg_id)

    await bot.send_message(
        chat_id=chat_id,
        parse_mode="MarkdownV2",
        text=escape(f'current model: `{operation}`')
    )


def register(bot: AsyncTeleBot, decorator) -> None:
    handler = decorator(handle_models)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])


action = {
    "name": 'models',
    "description": 'list models: /models [model_name]',
    "handler": do_model_change,
    "delete_after_invoke": True
}
