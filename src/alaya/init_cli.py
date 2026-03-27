async def init_db():
    ensure = input("初始化数据库将清空现有数据，请确认(Y/N): ")
    if ensure.strip().lower()[0] != "y":
        print("Bye!")
        return

    import warnings
    from aiomysql import Warning as mysql_warning
    warnings.filterwarnings("ignore", category=mysql_warning)
    from . import logger, conf, db_pool_name
    from .constants import INIT_RSS_SCRIPTS
    from hurag.dss import rss

    pool = await rss.get_pool(
        host=conf.mariadb.host,
        port=conf.mariadb.port,
        user=conf.mariadb.user,
        password=conf.mariadb.password,
        db=conf.mariadb.database,
        pool_name=db_pool_name,
    )
    try:
        async with pool.acquire() as conn, conn.cursor() as cur:
            for stmt in INIT_RSS_SCRIPTS:
                if not stmt:
                    continue
                await cur.execute(stmt)
            await conn.commit()
            logger.info("HuRAG WebUI database is initialized.")
            print("HuRAG WebUI 数据库已初始化。")
    except Exception as e:
        await conn.rollback()
        logger.error(f"Error while initializing the database: {e!r}")
        print("初始化数据库失败，请查看日志。")
        raise e
    finally:
        await rss.close_pool()

def main():
    import asyncio
    asyncio.run(init_db())
