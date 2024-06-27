import importlib

from ..types import ShareType, Configuration, Preview
from ..storage.types import Topic
from . import telegraph

share_providers = {}
default_providers = {}


async def init_providers(providers: list[dict], config: Configuration):
    module_info = {}

    types = {m.name.lower(): m.value for m in ShareType}

    for provider in providers:
        assert provider.get("name"), "share name can't be empty"

        module_name = provider.get("type")
        if module_name not in types:
            raise Exception(f"Invalid share type: {module_name}")

        params = provider.copy()
        params["proxy"] = config.proxy_url

        module = module_info.get(module_name)
        if not module:
            module = importlib.import_module(f".{module_name}", __package__)
            module_info[module_name] = module

        instance = await module.create(params, config)
        if not instance:
            raise Exception(f"Got none from module: {module_name}")

        share_providers[provider["name"]] = instance
        default_providers[module_name] = instance

    if Preview.TELEGRAPH.value not in default_providers:
        module = importlib.import_module(f".telegraph", __package__)
        instance = await module.create({}, config)
        share_providers["telegraph"] = instance
        default_providers[Preview.TELEGRAPH.value] = instance


async def share(name: str, convo: Topic):
    provider = share_providers.get(name)
    if not provider:
        raise Exception(f"Unknown share provider: {name}")

    return await provider.share(convo)


def get_provider_by_type(preview_type: Preview):
    if preview_type.value in default_providers:
        return default_providers[preview_type.value]

    return None
