from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.md2tgmd import escape
from ..context import profiles, config, get_bot_name, Endpoint
from ..storage import types

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
    "4o": "gpt-4o",
    "g2": "gemini-2.0-flash",
    "g2think": "gemini-2.0-flash-thinking-exp-01-21",
    "g2pro": "gemini-2.0-pro-exp-02-05",
    "v3": "deepseek-chat",
    "r1": "deepseek-reasoner",
}


async def handle_models(message: Message, bot: AsyncTeleBot):
    uid = message.from_user.id
    profile = await profiles.load(uid, message.chat.id, message.message_thread_id)
    bot_name = await get_bot_name()
    endpoint = config.get_endpoint(profile.endpoint or "None")

    text = message.text.replace("/model", "").replace(bot_name, "").strip()
    models = endpoint.models or []
    # fast switch
    if len(text) > 0:
        if text in models:
            await _do_model_change(
                bot=bot,
                profile=profile,
                model=text,
                msg_ids=[message.message_id],
                chat_id=message.chat.id,
                uid=uid,
                thread_id=message.message_thread_id,
            )
            return
        elif SHORT_NAME.get(text, None) in models:
            await _do_model_change(
                bot=bot,
                profile=profile,
                model=SHORT_NAME[text],
                msg_ids=[message.message_id],
                chat_id=message.chat.id,
                uid=uid,
                thread_id=message.message_thread_id,
            )
            return

    await display_models(
        bot=bot,
        profile=profile,
        endpoint=endpoint,
        message_id=message.message_id,
        chat_id=message.chat.id,
        uid=uid,
        thread_id=message.message_thread_id,
    )


async def display_models(
    bot: AsyncTeleBot,
    profile: types.Profile,
    endpoint: Endpoint,
    message_id: int,
    chat_id: int,
    uid: int,
    thread_id: int = None,
):
    context = f"{message_id}:{chat_id}:{uid}"
    keyboard = []
    items = []
    models = endpoint.models or []

    for idx, model in enumerate(models):
        callback_data = f'{action["name"]}:{idx}:{context}'
        if len(items) == 2:
            keyboard.append(items)
            items = []
        items.append(InlineKeyboardButton(model, callback_data=callback_data))

    if len(items) > 0:
        keyboard.append(items)
        keyboard.append(
            [
                InlineKeyboardButton(
                    "dismiss", callback_data=f'{action["name"]}:dismiss:{context}'
                )
            ]
        )

    msg_text = f'current endpoint: `{profile.endpoint or "None"}`\ncurrent model: `{profile.model or "None"}`\n'
    await bot.send_message(
        chat_id=chat_id,
        text=escape(msg_text),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
        message_thread_id=thread_id,
    )


async def do_model_change(
    bot: AsyncTeleBot,
    operation: str,
    msg_ids: list[int],
    chat_id: int,
    uid: int,
    message: Message,
):
    if operation == "dismiss":
        await bot.delete_messages(chat_id, [message.message_id, msg_ids[0]])
        return

    profile = await profiles.load(uid, chat_id, message.message_thread_id)
    endpoint = config.get_endpoint(profile.endpoint or "None")
    if endpoint is None:
        return

    try:
        model_idx = int(operation)
        models = endpoint.models or []
        if 0 <= model_idx < len(models):
            model = models[model_idx]
            await _do_model_change(
                bot=bot,
                profile=profile,
                model=model,
                msg_ids=msg_ids + [message.message_id],
                chat_id=chat_id,
                uid=uid,
                thread_id=message.message_thread_id,
            )
    except ValueError:
        # 处理operation不是数字的情况
        pass


async def _do_model_change(
    bot: AsyncTeleBot,
    profile: types.Profile,
    model: str,
    msg_ids: list[int],
    chat_id: int,
    uid: int,
    thread_id: int = None,
):
    if profile.model != model:
        message_id = msg_ids[0]
        endpoint = config.get_endpoint(profile.endpoint or "None")
        if endpoint is None:
            await bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=message_id,
                parse_mode="MarkdownV2",
                text=escape(f"endpoint not found"),
                message_thread_id=thread_id,
            )
            return

        if model not in (endpoint.models or []):
            await bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=message_id,
                parse_mode="MarkdownV2",
                text=escape(f"current endpoint does not support the model `{model}`"),
                message_thread_id=thread_id,
            )
            return

        profile.model = model
        await profiles.update_model(uid, chat_id, thread_id, profile.model)

    await bot.send_message(
        chat_id=chat_id,
        parse_mode="MarkdownV2",
        text=escape(f"current model: `{model}`"),
        message_thread_id=thread_id,
    )
    await bot.delete_messages(chat_id, msg_ids)


def register(bot: AsyncTeleBot, decorator, action_provider):
    handler = decorator(handle_models)
    bot.register_message_handler(handler, pass_bot=True, commands=[action["name"]])

    action_provider[action["name"]] = do_model_change

    return action


action = {
    "name": "model",
    "description": "display models: [model_name]",
    "order": 60,
}
