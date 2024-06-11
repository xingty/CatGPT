import enum
import abc

from contextvars import ContextVar

import storage


class TxState(enum.Enum):
    Init = 0
    Committed = 1
    Rollback = 2
    Close = 3


class Transactional(abc.ABC):
    async def get_transaction(self, tx_type="read"):
        return await get_transaction(tx_type)

    async def retrieve_transaction(self):
        tx = context.get()
        if tx is None:
            raise Exception("Transaction not found")

        return tx


class Transaction:
    def __init__(self, connection, tx_type="read"):
        self.connection = connection
        connection.set_trace_callback(print)
        self.tx_type = tx_type
        self.state = TxState.Init

    def commit(self):
        self.connection.commit()
        self.state = TxState.Committed

    def rollback(self):
        self.connection.rollback()
        self.state = TxState.Rollback

    def close(self):
        self.connection.close()
        self.state = TxState.Close

    def is_end(self):
        return self.state != TxState.Init


context: [Transaction | None] = ContextVar("transaction", default=None)


def transactional(tx_type: str = "read"):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            token = None
            tx = context.get()
            if tx is None:
                if tx_type == "write":
                    conn = await storage.datasource.get_write_conn()
                else:
                    conn = await storage.datasource.get_read_conn()

                tx = Transaction(conn, tx_type)
                token = context.set(tx)

            if tx_type == "write" and tx.tx_type != tx_type:
                raise Exception("A read transaction cannot join a write transaction")

            try:
                result = await func(*args, **kwargs)
                # reenter
                if token is not None and (not tx.is_end()):
                    tx.commit()

                return result
            except Exception as e:
                if token is not None and (not tx.is_end()):
                    tx.rollback()

                print(e)
                raise e
            finally:
                if token is not None:
                    context.reset(token)
                    tx.close()

        return wrapper

    return decorator


async def get_transaction(tx_type: str):
    tx = context.get()
    if tx is not None:
        return tx

    if tx_type == "write":
        conn = await storage.datasource.get_write_conn()
    else:
        conn = await storage.datasource.get_read_conn()

    return Transaction(conn, tx_type)
