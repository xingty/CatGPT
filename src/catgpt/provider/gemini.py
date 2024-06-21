import google.generativeai as genai
from google.generativeai.client import _ClientManager

from ..storage import types
from ..types import MessageType, Endpoint
from ..utils import tg_image

_client_manager_cache = {}
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]


def message2payload(messages: list[types.Message]) -> list:
    contents = []
    for m in messages:
        role = "model" if m.role == "assistant" else "user"
        parts = []

        if m.message_type == MessageType.PHOTO.value and m.media_url:
            bin_data = tg_image.decode_image(m.media_url)
            parts.append({"mime_type": "image/jpeg", "data": bin_data})

        if m.content:
            parts.append({"text": m.content})

        if len(parts) > 0:
            contents.append({"role": role, "parts": parts})

    return contents


def get_model(endpoint: Endpoint, body: dict):
    if endpoint.name in _client_manager_cache:
        _client_manager = _client_manager_cache[endpoint.name]
    else:
        _client_manager = _ClientManager()
        _client_manager.configure(api_key=endpoint.secret_key)
        _client_manager_cache[endpoint.name] = _client_manager

    model = genai.GenerativeModel(
        model_name=body.get("model") or "gemini-1.5-flash",
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    model._async_client = _client_manager.get_default_client("generative_async")

    return model


async def do_ask(endpoint: Endpoint, body: dict, stream=True):
    model = get_model(endpoint, body)
    contents = message2payload(body.get("messages", []))
    async for chunk in await model.generate_content_async(
        contents=contents, stream=stream
    ):
        if not chunk.candidates:
            continue

        content = chunk.candidates[0].content
        if content.parts:
            yield {
                "role": "assistant" if content.role == "model" else "user",
                "content": content.parts[0].text,
                "finished": False,
            }

    yield {"finished": True, "role": "assistant", "content": ""}


async def ask_stream(endpoint: Endpoint, body: dict):
    async for chunk in do_ask(endpoint, body, stream=True):
        yield chunk


async def ask(endpoint: Endpoint, body: dict):
    async for chunk in do_ask(endpoint, body, stream=False):
        return chunk.get("content", "")

    return ""
