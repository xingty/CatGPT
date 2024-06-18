from ..storage import types

MODELS = {
    "gpt-4o": "2023-10",
    "gpt-4-turbo-2024-04-09": "2023-11",
    "gpt-4-0125-preview": "2023-11",
    "gpt-4-1106-preview": "2023-04",
    "gpt-4-turbo": "2023-11",
    "gpt-4": "2023-09",
}

DEFAULT_SYSTEM_TEMPLATE = """
You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: {cutoff}
Current model: {model}
`;
"""


def get_system_prompt(model):
    if model.startswith("gpt-4"):
        cutoff = MODELS.get(model, "2023-09")
        return DEFAULT_SYSTEM_TEMPLATE.format(
            cutoff=cutoff,
            model=model,
        )

    return None


def get_prompt(prompt) -> types.Message | None:
    if prompt:
        return types.Message(
            role="system", content=prompt, message_id=0, chat_id=0, ts=0, topic_id=0
        )

    return None
