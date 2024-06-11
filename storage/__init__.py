from contextvars import ContextVar
from abc import ABC, abstractmethod

from .types import Topic, Message


class Datasource(ABC):
    @abstractmethod
    async def get_write_conn(self):
        pass

    @abstractmethod
    async def get_read_conn(self):
        pass


datasource: Datasource | None = None
