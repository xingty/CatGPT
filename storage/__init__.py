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


class Transaction:
    def __init__(self, datasource: Datasource):
        self.datasource = datasource
        self.context = ContextVar("connection", default=None)

    def transactional(self, tx_type: str = "read"):
        print(tx_type)

        def decorator(func):
            async def wrapper(*args, **kwargs):
                conn = self.context.get()
                token = None
                if conn is None:
                    if tx_type == "write":
                        conn = await self.datasource.get_write_conn()
                    else:
                        conn = await self.datasource.get_read_conn()
                    token = self.context.set(conn)

                try:
                    await func(*args, **kwargs)
                    conn.commit()
                except Exception as e:
                    print(e)
                    conn.rollback()
                finally:
                    if tx_type == "read":
                        conn.close()

            return wrapper

        return decorator

    # def __getattribute__(self, item: str):
    #     val = super().__getattribute__(item)
    #
    #     if callable(val):
    #         print("Name", self.name)  # you can access the instance name here
    #         return function_decorator(val)
    #     return val
