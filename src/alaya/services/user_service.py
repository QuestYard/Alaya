from ..utilities import generate_id
from .. import rss
from ..models import User


async def get_user(account: str) -> User | None:
    resp = await rss.query(
        "SELECT id, account, username, user_path FROM users WHERE account = %s",
        (account,),
        as_dict=True,
    )
    return User(**resp[0]) if resp else None


async def get_user_by_id(id: str) -> User | None:
    resp = await rss.query(
        "SELECT id, account, username, user_path FROM users WHERE id = %s",
        (id,),
        as_dict=True,
    )
    return User(**resp[0]) if resp else None


async def is_account_exist(account: str) -> bool:
    resp = await rss.query("SELECT 1 FROM users WHERE account = %s", (account,))
    return bool(resp)


async def is_user_id_exist(user_id: str) -> bool:
    resp = await rss.query("SELECT 1 FROM users WHERE id = %s", (user_id,))
    return bool(resp)


async def is_user_valid(user_id: str, account: str) -> bool:
    resp = await rss.query(
        "SELECT 1 FROM users WHERE id = %s AND account = %s", (user_id, account)
    )
    return bool(resp)


async def upsert_user(account, username, user_path) -> User:
    _ = await rss.dml(
        """
        INSERT INTO users (id, account, username, user_path)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            user_path = VALUES(user_path)
        """,
        (generate_id(), account, username, user_path),
    )
    user = await get_user(account)
    return user if user else User()


async def login(account: str, password: str | None) -> User:
    if account.lower() == "guest":
        return User()

    from ..services import sso_authenticate

    sso_info = await sso_authenticate(account, password)
    return await upsert_user(**sso_info)
