from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from utils.md2tgmd import escape
from context import profiles, config, get_bot_name

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
    uid = message.from_user.id
    profile = await profiles.load(uid)
    bot_name = await get_bot_name()
    endpoint = config.get_endpoint(profile.endpoint or "None")

    text = message.text.replace("/models", "").replace(bot_name, "").strip()
    models = endpoint.models or []
    # fast switch
    if len(text) > 0:
        if text in models:
            await do_model_change(bot, text, message.message_id, message.chat.id, uid, message)
            return
        elif SHORT_NAME.get(text, None) in models:
            await do_model_change(bot, SHORT_NAME[text], message.message_id, message.chat.id, uid, message)
            return

    context = f'{message.message_id}:{message.chat.id}:{uid}'
    keyboard = []
    items = []

    for model in (endpoint.models or []):
        callback_data = f'{action["name"]}:{model}:{context}'
        if len(items) == 2:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(model, callback_data=callback_data))

    if len(items) > 0:
        keyboard.append(items)
        keyboard.append([InlineKeyboardButton("dismiss", callback_data=f'{action["name"]}:dismiss:{context}')])

    msg_text = f'current endpoint: `{profile.endpoint or "None"}`\ncurrent model: `{profile.model or "None"}`\n'
    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(msg_text),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def do_model_change(bot: AsyncTeleBot, operation: str, msg_ids: list[int], chat_id: int, uid: int, message: Message):
    if operation == "dismiss":
        await bot.delete_messages(chat_id, [message.message_id, msg_ids[0]])
        return

    profile = await profiles.load(uid)
    message_id = msg_ids[0]
    endpoint = config.get_endpoint(profile.endpoint or "None")
    if endpoint is None:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            parse_mode="MarkdownV2",
            text=escape(f'endpoint not found')
        )
        return

    if operation not in (endpoint.models or []):
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            parse_mode="MarkdownV2",
            text=escape(f'current endpoint does not support the model `{operation}`')
        )
        return

    profile.model = operation
    await profiles.update_model(uid, profile.model)

    await bot.send_message(
        chat_id=chat_id,
        parse_mode="MarkdownV2",
        text=escape(f'current model: `{operation}`')
    )
    await bot.delete_messages(chat_id, [message_id, message.message_id])


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_models)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])

    action_provider[action["name"]] = do_model_change

    return action


action = {
    "name": 'models',
    "description": 'list models: [model_name]',
    "order": 60,
}
