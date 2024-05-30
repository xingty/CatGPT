import json

from openai import AsyncOpenAI
from utils.prompt import get_system_prompt


def inject_system_prompt_if_need(messages: list, endpoint: dict, model: str):
    if messages[0].get("role") == "system":
        return

    prompt = get_system_prompt(model)
    if prompt:
        messages.insert(0, {
            "role": "system",
            "content": prompt
        })


async def ask_stream(endpoint: dict, body: dict):
    client = AsyncOpenAI(
        base_url=endpoint["api_url"],
        api_key=endpoint["secret_key"]
    )

    messages = body.get('messages', [])
    model = body.get('model')
    inject_system_prompt_if_need(messages, endpoint, model)
    assert len(messages) > 0, "messages should not be empty"
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=body.get('temperature', 0.6),
        stream=True,
        presence_penalty=body.get('presence_penalty', 0.0),
        frequency_penalty=body.get('frequency_penalty', 0.0),
        top_p=body.get('top_p', 1),
    )

    async for chunk in response:
        choice = chunk.choices[0]
        yield {
            "role": choice.delta.role,
            "content": choice.delta.content,
            "finished": choice.finish_reason
        }


async def ask(endpoint: dict, body: dict):
    client = AsyncOpenAI(
        base_url=endpoint["api_url"],
        api_key=endpoint["secret_key"]
    )

    response = await client.chat.completions.create(
        model=endpoint.get('default_model', 'gpt-3.5-turbo'),
        messages=body.get('messages'),
        temperature=body.get('temperature', 0.7),
        stream=False,
        presence_penalty=body.get('presence_penalty', 0.0),
        frequency_penalty=body.get('frequency_penalty', 0.0),
        top_p=body.get('top_p', 1),
    )

    return response.choices[0].message.content
