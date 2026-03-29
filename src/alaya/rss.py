import aiomysql
import asyncio
from functools import wraps
from typing import Any
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

_pools: dict[str, aiomysql.Pool] = {}
_pools_lock: asyncio.Lock = asyncio.Lock()


async def get_pool(
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    db: str | None = None,
    pool_name: str = "default",
) -> aiomysql.Pool:
    """Get or create the database connection pool."""
    from . import conf

    global _pools

    if pool_name in _pools:
        return _pools[pool_name]

    async with _pools_lock:
        if pool_name in _pools:
            return _pools[pool_name]
        _pools[pool_name] = await aiomysql.create_pool(
            host=host or conf.db.host,
            port=port or conf.db.port,
            user=user or conf.db.user,
            password=password or conf.db.password,
            db=db or conf.db.database,
            autocommit=False,
            minsize=1,
            maxsize=10,
            pool_recycle=3600,
        )

    return _pools[pool_name]


async def close_pool(pool_name: str | None = None) -> None:
    """Close the database connection pool."""
    global _pools
    if pool_name:
        if pool_name in _pools:
            pool = _pools.pop(pool_name)
            pool.close()
            await pool.wait_closed()
    else:
        for pool in _pools.values():
            pool.close()
            await pool.wait_closed()
        _pools.clear()


@asynccontextmanager
async def lifespan():
    """Context manager to handle database pool lifecycle."""
    try:
        yield
    finally:
        await close_pool()


def with_rdb(
    func=None,
    *,
    connection_arg_name="connection",
    cursor_arg_name="cursor",
    dict_cursor=False,
    ss_cursor=False,
    pool_name="default",
) -> Callable[..., Any]:
    """
    Decorator for injection of rss connection and cursor.

    Args:
        func:
            The function to be decorated.
        connection_arg_name: optional, default "connection"
            The name of the connection argument to be injected.
        cursor_arg_name: optional, default "cursor"
            The name of the cursor argument to be injected.
        dict_cursor: optional, default False
            Whether to use a dictionary cursor.
        ss_cursor: optional, default False
            Whether to use a server-side cursor.
        pool_name: optional, default "default"
            The name of the connection pool to use.

    **Usage**:

    The most common usage is to inject connection and ordinary cursor with
    default names, ordinary cursor.

    There should be two arguments named "connection" and "cursor" in
    the decorated function.

    ```python
    @with_rdb
    async def my_function(connection, cursor, other_arg):
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Connection and cursor can also be injected into the decorated function
    as keyword arguments.

    ```python
    @with_rdb
    async def my_function(other_arg, **kwargs):
        connection = kwargs['connection']
        cursor = kwargs['cursor']
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Or you can customize the names of the injected arguments.

    ```python
    @with_rdb(connection_arg_name="conn", cursor_arg_name="cur", dict_cursor=True)
    async def my_function(other_arg, **kwargs):
        connection = kwargs['conn']
        cursor = kwargs['cur']
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Type of cursor can also be specified. There are four types of cursor:

    - Ordinary cursor (default): `dict_cursor=False`, `ss_cursor=False`
    - Dictionary cursor: `dict_cursor=True`, `ss_cursor=False`
    - Server-side ordinary cursor: `dict_cursor=False`, `ss_cursor=True`
    - Server-side dictionary cursor: `dict_cursor=True`, `ss_cursor=True`

    **Caution**:

    - The decorated function *MUST* be asynchronous.
    - *DO NOT* close the connection or cursor in the decorated function.

    Returns:
        The decorated function.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            pool = await get_pool(pool_name=pool_name)
            connection = await pool.acquire()
            if dict_cursor:
                if ss_cursor:
                    cursor = await connection.cursor(aiomysql.SSDictCursor)
                else:
                    cursor = await connection.cursor(aiomysql.DictCursor)
            else:
                if ss_cursor:
                    cursor = await connection.cursor(aiomysql.SSCursor)
                else:
                    cursor = await connection.cursor()
            kwargs[connection_arg_name] = connection
            kwargs[cursor_arg_name] = cursor
            try:
                ret = await func(*args, **kwargs)
                await connection.commit()
                return ret
            except Exception:
                await connection.rollback()
                raise
            finally:
                await cursor.close()
                pool.release(connection)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


async def query(
    statement: str,
    data: tuple = (),
    as_dict: bool = False,
    pool_name: str = "default",
) -> list[Any]:
    """
    Execute a SQL query statement (SELECT) and return all results.

    Args:
        statement:
            The SQL query statement to be executed.
        data:
            The data to be used in the query statement.
        as_dict:
            Whether returns rows in list of dict or not.
        pool_name:
            The name of the connection pool to use. Default is "default".

    Returns:
        A list of tuples or dicts representing the query results.
    """
    pool = await get_pool(pool_name=pool_name)
    async with (
        pool.acquire() as conn,
        conn.cursor(aiomysql.DictCursor) if as_dict else conn.cursor() as cur,
    ):
        await cur.execute(statement, data)
        ret = await cur.fetchall()
        await conn.commit()
        return list(ret)


async def query_iter(
    statement: str,
    data: tuple = (),
    batch_size: int = 1000,
    as_dict: bool = False,
    pool_name: str = "default",
) -> AsyncGenerator[Any]:
    """
    Execute a SQL query statement (SELECT) and yield results iteratively.
    Uses a server-side cursor to avoid loading all results into memory.

    Args:
        statement:
            The SQL query statement to be executed.
        data:
            The data to be used in the query statement.
        batch_size:
            The number of rows to fetch at a time. Default is 1000.
        as_dict:
            Whether returns rows in list of dict or not.
        pool_name:
            The name of the connection pool to use. Default is "default".

    Yields:
        A tuple or a dict representing a row in the query results.
    """
    pool = await get_pool(pool_name=pool_name)
    async with (
        pool.acquire() as conn,
        conn.cursor(aiomysql.SSDictCursor)
        if as_dict
        else conn.cursor(aiomysql.SSCursor) as cur,
    ):
        await cur.execute(statement, data)
        while True:
            rows = await cur.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield row
        await conn.commit()


async def dml(
    statement: str,
    data: tuple | list[tuple] | None = (),
    pool_name: str = "default",
) -> int:
    """
    Execute a DML statement (INSERT, UPDATE, DELETE).

    Args:
        statement:
            The DML statement to be executed.
        data:
            The data to be used in the DML statement. If a list of tuples is
            provided, executemany() will be used.
        pool_name:
            The name of the connection pool to use. Default is "default".

    Returns:
        The number of affected rows.
    """
    pool = await get_pool(pool_name=pool_name)
    async with pool.acquire() as conn, conn.cursor() as cur:
        try:
            if data is not None and isinstance(data, list):
                await cur.executemany(statement, data)
            else:
                await cur.execute(statement, data or ())
            await conn.commit()

            return cur.rowcount
        except Exception:
            await conn.rollback()
            raise


async def transact(
    statements: list[str],
    data: list[tuple | list[tuple] | None] | None = None,
    pool_name: str = "default",
) -> int:
    """
    Execute multiple DML statements in a transaction.
    Args:
        statements:
            A list of DML statements to be executed.
        data:
            A list of data tuples or list of tuples corresponding to each
            statement. If None, empty tuples will be used. If the length of
            data is less than statements, the remaining statements will use
            empty tuples.
        pool_name:
            The name of the connection pool to use. Default is "default".

    Returns:
        The total number of affected rows.
    """
    pool = await get_pool(pool_name=pool_name)
    async with pool.acquire() as conn, conn.cursor() as cur:
        ns = len(statements)
        if data is None:
            data = [() for _ in range(len(statements))]
        nd = len(data)
        if ns > nd:
            data.extend([()] * (ns - nd))
        try:
            rowcount = 0
            for st, dt in zip(statements[:ns], data[:ns]):
                if dt is not None and isinstance(dt, list):
                    await cur.executemany(st, dt)
                else:
                    await cur.execute(st, dt or ())
                rowcount += cur.rowcount
            await conn.commit()

            return rowcount
        except Exception:
            await conn.rollback()
            raise
