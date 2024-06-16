from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.md2tgmd import escape
from ..context import profiles, config, get_bot_name
from ..context import Endpoint


async def handle_endpoints(message: Message, bot: AsyncTeleBot):
    bot_name = await get_bot_name()
    endpoint_name = message.text.replace("/endpoints", "").replace(bot_name, "").strip()
    uid = message.from_user.id
    # fast switch
    if len(endpoint_name) > 0:
        endpoint = config.get_endpoint(endpoint_name)
        if endpoint is not None:
            await do_endpoint_change(bot, endpoint_name, [message.message_id], message.chat.id, uid, message)
            return

    profile = await profiles.load(uid)
    context = f'{message.message_id}:{message.chat.id}:{uid}'
    keyboard = []
    items = []

    for endpoint in config.get_endpoints():
        name = endpoint.name
        callback_data = f'{action["name"]}:{name}:{context}'
        if len(items) == 2:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(name, callback_data=callback_data))

    if len(items) > 0:
        keyboard.append(items)
        keyboard.append([InlineKeyboardButton("dismiss", callback_data=f'{action["name"]}:dismiss:{context}')])

    endpoint_name = profile.endpoint or "None"
    text = f'current endpoint: **{endpoint_name}** \nEndpoints:'
    await bot.send_message(
        chat_id=message.chat.id,
        text=escape(text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def do_endpoint_change(bot: AsyncTeleBot, operation: str, msg_ids: list[int], chat_id: int, uid: int, message: Message):
    message_id = msg_ids[0]
    if operation == "dismiss":
        await bot.delete_messages(chat_id, [message_id, message.message_id])
        return

    endpoint: Endpoint = config.get_endpoint(operation)
    if endpoint is None:
        await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message_id,
            parse_mode="MarkdownV2",
            text=escape(f'endpoint not found')
        )
        return

    models = endpoint.models
    profile = await profiles.load(uid)
    profile.endpoint = operation
    if profile.model not in models:
        profile.model = endpoint.default_model

    await profiles.update(uid, profile)

    await bot.send_message(
        chat_id=chat_id,
        reply_to_message_id=message_id,
        parse_mode="MarkdownV2",
        text=escape(f'current endpoint: `{operation}`')
    )
    await bot.delete_messages(chat_id, [message_id, message.message_id])


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_endpoints)
    bot.register_message_handler(handler, pass_bot=True, commands=[action['name']])

    action_provider[action["name"]] = do_endpoint_change

    return action


action = {
    "name": 'endpoints',
    "description": 'list endpoints: [endpoint_name]',
    "delete_after_invoke": True,
    "order": 50,
}
