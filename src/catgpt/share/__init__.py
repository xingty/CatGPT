import importlib

from ..types import ShareType, Configuration
from ..storage.types import Topic

share_providers = {}


def init_providers(providers: list[dict], config: Configuration):
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

        instance = module.create(params)
        if not instance:
            raise Exception(f"Got none from module: {module_name}")

        share_providers[provider["name"]] = instance


async def share(name: str, convo: Topic):
    provider = share_providers.get(name)
    if not provider:
        raise Exception(f"Unknown share provider: {name}")

    return await provider.share(convo)
