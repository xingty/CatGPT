import enum

MODEL_MAPPING = {
    "gpt-4o": ["text", "photo"],
    "gpt-4-1106-preview": ["text", "photo"],
    "gpt-4-0125-preview": ["text", "photo"],
    "gpt-4-turbo-preview": ["text", "photo"],
    "gpt-4-turbo-2024-04-09": ["text", "photo"],
    "gpt-4-turbo": ["text", "photo"],
    "gpt-4": ["text"],
    "gpt-3.5-turbo": ["text"],
    "gpt-3.5-turbo-0301": ["text"],
    "gpt-4-0613": ["text"],
}


class Endpoint:

    def __init__(
        self,
        name: str,
        api_url: str,
        secret_key: str,
        models: list[str],
        provider: str = "openai",
        default_model: str = None,
        default_endpoint: bool = False,
        generate_title: bool = True,
    ):
        assert len(name) > 0, "endpoint name can't be empty"
        assert len(api_url) > 0, "api url can't be empty"
        assert len(secret_key) > 0, "secret key can't be empty"
        assert len(models) > 0, "models can't be empty"
        assert provider in ["openai", "gemini", "qwen"], "provider not supported"

        self.name = name
        self.api_url = api_url
        self.secret_key = secret_key
        self.models = models
        self.generate_title = generate_title
        self.default_endpoint = default_endpoint
        self.provider = Provider[provider.upper()]
        self.default_model = default_model
        if not default_model:
            self.default_model = models[0]

    @staticmethod
    def is_support(model, message_type):
        return message_type in MODEL_MAPPING.get(model, [])

    def __str__(self):
        return f"""
        Endpoint(
            name={self.name}, 
            api_url={self.api_url}, 
            default_model={self.default_model}, 
            models={self.models},
            default_endpoint={self.default_endpoint},
            generate_title={self.generate_title},
            provider={self.provider}
        )"""


class Provider(enum.Enum):
    OPENAI = "oai"
    GEMINI = "gemini"
    QWEN = "qwen"


class MessageType(enum.Enum):
    TEXT = 0
    PHOTO = 1
    AUDIO = 2


class ChatType(enum.Enum):
    PRIVATE = 0
    GROUP = 10
    CHANNEL = 20

    @staticmethod
    def get(chat_type: str):
        if chat_type == "private":
            return ChatType.PRIVATE

        if chat_type == "channel":
            return ChatType.CHANNEL

        return ChatType.GROUP
