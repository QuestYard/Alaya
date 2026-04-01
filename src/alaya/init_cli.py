async def init_db():
    ensure = input("初始化数据库将清空现有数据，请确认(Y/N): ")
    if ensure.strip().lower()[0] != "y":
        print("Bye!")
        return

    from . import logger, rss
    from .constants import INIT_RSS_SCRIPTS

    try:
        import warnings
        from aiomysql import Warning as mysql_warning
        warnings.filterwarnings("ignore", category=mysql_warning)

        pool = await rss.get_pool()
        async with pool.acquire() as conn, conn.cursor() as cur:
            try:
                for stmt in INIT_RSS_SCRIPTS:
                    if not stmt:
                        continue
                    await cur.execute(stmt)
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

        logger.info("Alaya database is initialized.")
        print("Alaya 数据库已初始化。")
    except Exception as e:
        logger.error(f"Error while initializing the database: {e!r}")
        print("初始化数据库失败，请查看日志。")
        raise
    finally:
        await rss.close_pool()

def main():
    import asyncio
    asyncio.run(init_db())
