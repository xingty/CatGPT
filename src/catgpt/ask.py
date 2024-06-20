from openai import AsyncOpenAI

from .storage import types
from .types import Endpoint, Provider

from .provider import oai


def message2payload(endpoint: Endpoint, messages: list[types.Message]) -> list[dict]:
    if endpoint.provider == Provider.OPENAI:
        return oai.message2payload(messages)

    raise NotImplementedError


async def ask_stream(endpoint: Endpoint, body: dict):
    if endpoint.provider == Provider.OPENAI:
        return oai.ask_stream(endpoint, body)

    raise Exception("Provider not supported")


async def ask(endpoint: Endpoint, body: dict):
    client = AsyncOpenAI(base_url=endpoint.api_url, api_key=endpoint.secret_key)

    response = await client.chat.completions.create(
        model=endpoint.default_model or "gpt-3.5-turbo",
        messages=body.get("messages"),
        temperature=body.get("temperature", 0.7),
        stream=False,
        presence_penalty=body.get("presence_penalty", 0.0),
        frequency_penalty=body.get("frequency_penalty", 0.0),
        top_p=body.get("top_p", 1),
    )

    return response.choices[0].message.content
