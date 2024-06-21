import importlib

from pathlib import Path

from ..storage import types
from ..types import Endpoint

providers = {
    # Provider.OPENAI: None,
    # Provider.GEMINI: None,
}


def get_provider(endpoint: Endpoint):
    module_name = endpoint.provider.value
    provider = providers.get(module_name, None)

    if provider is None and Path(__file__).parent.joinpath(f"{module_name}.py").exists():
        provider = importlib.import_module(f".{module_name}", __package__)
        providers[module_name] = provider
        return provider

    return provider


def message2payload(endpoint: Endpoint, messages: list[types.Message]) -> list:
    provider = get_provider(endpoint)
    if provider is None:
        raise Exception("Provider not supported")

    return provider.message2payload(messages)


async def ask_stream(endpoint: Endpoint, body: dict):
    provider = get_provider(endpoint)
    if provider is None:
        raise Exception("Provider not supported")

    messages = body.get("messages", [])
    if not messages:
        raise Exception("No messages")

    return provider.ask_stream(endpoint, body)


async def ask(endpoint: Endpoint, body: dict):
    provider = get_provider(endpoint)
    if provider is None:
        raise Exception("Provider not supported")

    messages = body.get("messages", [])
    if not messages:
        raise Exception("No messages")

    return await provider.ask(endpoint, body)

