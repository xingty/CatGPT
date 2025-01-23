from openai import AsyncOpenAI

from ..storage import types
from ..context import Endpoint
from ..utils.prompt import get_system_prompt
from ..types import MessageType


def inject_system_prompt_if_need(messages: list, model: str):
    if messages[0].get("role") == "system":
        return

    prompt = get_system_prompt(model)
    if prompt:
        messages.insert(0, {"role": "system", "content": prompt})


def message2payload(messages: [types.Message]) -> list[dict]:
    messages_payload = []
    for m in messages:
        if m.message_type in [MessageType.TEXT.value, MessageType.DOCUMENT.value]:
            messages_payload.append({"role": m.role, "content": m.content})
        else:
            content = []
            is_online = m.media_url.startswith("https://") or m.media_url.startswith(
                "http://"
            )
            if len(m.content) > 0:
                content.append({"type": "text", "text": m.content})

            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            m.media_url
                            if is_online
                            else f"data:image/jpeg;base64,{m.media_url}"
                        )
                    },
                }
            )
            messages_payload.append({"role": m.role, "content": content})

    return messages_payload


async def ask_stream(endpoint: Endpoint, body: dict):
    client = AsyncOpenAI(base_url=endpoint.api_url, api_key=endpoint.secret_key)
    messages = message2payload(body.get("messages", []))
    response = await client.chat.completions.create(
        model=body.get("model"),
        messages=messages,
        temperature=body.get("temperature", 0.6),
        stream=True,
        presence_penalty=body.get("presence_penalty", 0.0),
        frequency_penalty=body.get("frequency_penalty", 0.0),
        top_p=body.get("top_p", 1),
    )

    async for chunk in response:
        if len(chunk.choices) == 0:
            continue

        choice = chunk.choices[0]
        reasoning = False
        # compatible with Deepseek
        if hasattr(choice.delta, 'reasoning_content'):
            reasoning = choice.delta.reasoning_content

        if reasoning:
            c = choice.delta.reasoning_content
        else:
            c = choice.delta.content

        yield {
            "role": choice.delta.role or "assistant",
            "content": c,
            "finished": choice.finish_reason,
            "reasoning": reasoning,
        }


async def ask(endpoint: Endpoint, body: dict):
    client = AsyncOpenAI(base_url=endpoint.api_url, api_key=endpoint.secret_key)
    messages = message2payload(body.get("messages", []))

    response = await client.chat.completions.create(
        model=endpoint.default_model or "gpt-3.5-turbo",
        messages=messages,
        temperature=body.get("temperature", 0.7),
        stream=False,
        presence_penalty=body.get("presence_penalty", 0.0),
        frequency_penalty=body.get("frequency_penalty", 0.0),
        top_p=body.get("top_p", 1),
    )

    if response.choices:
        return response.choices[0].message.content

    return ""
