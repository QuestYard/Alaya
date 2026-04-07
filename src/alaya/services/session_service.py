from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI

# from .. import db_pool_name, oa_client_name, oa_model_name
from ..models import Session, Message
# from ...llm import with_oa_client, chat_completion, extract_from_chat
from datetime import datetime


async def load_session_by_id(session_id: str) -> Session | None:
    """
    Load a session by its ID.

    Arguments:
        session_id: The ID of the session.

    Returns:
        The Session object if found, otherwise None.
    """
    if not session_id:
        return None

    from .. import rss

    query = "SELECT id, title, created_ts, user_id FROM sessions WHERE id = %s"
    rows = await rss.query(query, (session_id,), as_dict=True)
    if not rows:
        return None

    session = Session(**rows[0])
    return session


async def load_sessions_by_user(user_id: str, limit: int = 100) -> list[Session]:
    """
    Load recent sessions for a given user. Load all sessions if limit <= 0.

    Arugments:
        user_id: The ID of the user.
        limit: The maximum number of sessions to load.

    Returns:
        A list of Session objects.
    """
    if not user_id:
        return []

    from .. import rss

    query = """
    SELECT id, title, created_ts, user_id FROM sessions WHERE user_id = %s
    ORDER BY created_ts DESC
    """
    query += f"LIMIT {limit}" if limit > 0 else ""
    rows = await rss.query(query, (user_id,), as_dict=True)
    sessions = [Session(**row) for row in rows]

    return sessions


async def upsert_session(
    query: str,
    query_ts: datetime,
    response: str,
    response_ts: datetime,
    citation_ids: list[str] | None = None,
    session_id: str | None = None,
    title: str | None = None,
    user_id: str | None = None,
) -> tuple[Session | None, Message, Message]:
    """
    Insert new session or update existed session.

    Argument:
        query: user query.
        query_ts: timestamp of user query.
        response: LLM response.
        response_ts: timestamp of LLM response.
        citation_ids: list of citation IDs, empty if None.
        session_id: ID of an existed session or None when creating new session.
        title: title of the session, required when creating new session.
        user_id: ID of the user, required when creating new session.

    Return:
        A tuple containing:
            - The Session object, or None if updating an existed session.
            - The Message object for the user query.
            - The Message object for the LLM response.
    """
    from .. import rss
    from ..utilities import generate_id

    CREATE_NEW_SESSION = """
        INSERT INTO sessions (id, title, created_ts, user_id) VALUES (%s, %s, %s, %s)
    """
    INSERT_QUERY = """
        INSERT INTO session_messages
            (id, session_id, seq_no, role, content, created_ts, pair_id)
        VALUES
            (%s, %s, %s, 'user', %s, %s, %s)
    """
    INSERT_RESPONSE = """
        INSERT INTO session_messages
            (id, session_id, seq_no, role, content, created_ts, pair_id)
        VALUES
            (%s, %s, %s, 'assistant', %s, %s, %s)
    """
    INSERT_CITATIONS = """
        INSERT INTO query_segments (query_id, segment_id, seq_no) VALUES (%s, %s, %s)
    """
    GET_LAST_SEQ_NO = "SELECT max(seq_no) FROM session_messages WHERE session_id = %s"
    UPDATE_SESSION = "UPDATE sessions SET created_ts = %s WHERE id = %s"
    query_id = generate_id()
    response_id = generate_id()
    session_ts = datetime.now()
    # insert new session
    if not session_id:
        session_id = generate_id()
        statements = [
            CREATE_NEW_SESSION,
            INSERT_QUERY,
            INSERT_RESPONSE,
        ]
        data = [
            (session_id, title, session_ts, user_id),
            (query_id, session_id, 0, query, query_ts, response_id),
            (response_id, session_id, 1, response, response_ts, query_id),
        ]
        if citation_ids:
            statements.append(INSERT_CITATIONS)
            data.append(
                [(response_id, cid, seq + 1) for seq, cid in enumerate(citation_ids)]
            )
        await rss.transact(statements, data)
        assert title is not None, "title is required while inserting new session."
        assert user_id is not None, "user_id is required while inserting new session."
        s = Session(id=session_id, title=title, created_ts=session_ts, user_id=user_id)
        q = Message(
            id=query_id,
            session_id=session_id,
            seq_no=0,
            role="user",
            content=query,
            created_ts=query_ts,
            pair_id=response_id,
        )
        r = Message(
            id=response_id,
            session_id=session_id,
            seq_no=1,
            role="assistant",
            content=response,
            created_ts=response_ts,
            pair_id=query_id,
        )
        return s, q, r
    # update existed session
    pool = await rss.get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        await conn.begin()
        try:
            # Lock the session to prevent concurrent updates to seq_no
            await cur.execute(
                "SELECT 1 FROM sessions WHERE id = %s FOR UPDATE", (session_id,)
            )

            # Get the last seq_no
            await cur.execute(GET_LAST_SEQ_NO, (session_id,))
            row = await cur.fetchone()
            last_seq_no = row[0] if row and row[0] is not None else -1

            statements = [
                INSERT_QUERY,
                INSERT_RESPONSE,
                UPDATE_SESSION,
            ]
            data = [
                (query_id, session_id, last_seq_no + 1, query, query_ts, response_id),
                (
                    response_id,
                    session_id,
                    last_seq_no + 2,
                    response,
                    response_ts,
                    query_id,
                ),
                (session_ts, session_id),
            ]
            for stmt, datum in zip(statements, data):
                await cur.execute(stmt, datum)

            if citation_ids:
                await cur.executemany(
                    INSERT_CITATIONS,
                    [
                        (response_id, cid, seq + 1)
                        for seq, cid in enumerate(citation_ids)
                    ],
                )

            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    q = Message(
        id=query_id,
        session_id=session_id,
        seq_no=last_seq_no + 1,
        role="user",
        content=query,
        created_ts=query_ts,
        pair_id=response_id,
    )
    r = Message(
        id=response_id,
        session_id=session_id,
        seq_no=last_seq_no + 2,
        role="assistant",
        content=response,
        created_ts=response_ts,
        pair_id=query_id,
    )
    return None, q, r


async def load_messages_by_session(session_id: str) -> list[Message]:
    """
    Load messages for a given session.

    Arguments:
        session_id: The ID of the session.

    Returns:
        A list of Message objects.
    """
    if not session_id:
        return []

    from .. import rss

    query = """
    SELECT
        id,
        session_id,
        seq_no,
        role,
        content,
        created_ts,
        likes,
        dislikes,
        pair_id
    FROM session_messages
    WHERE session_id = %s
    ORDER BY seq_no ASC
    """
    rows = await rss.query(query, (session_id,), as_dict=True)
    messages = [Message(**row) for row in rows]

    return messages


async def load_citation_ids_by_session(session_id: str) -> dict[str, list[str]]:
    """
    Load citation IDs associated with queries in a given session.
    Arguments:
        session_id: The ID of the session.

    Returns:
        A dictionary mapping query IDs to lists of citation segment IDs.
    """
    if not session_id:
        return {}

    from .. import rss

    query = """
    SELECT qs.query_id, qs.segment_id
    FROM query_segments qs
    JOIN session_messages sm ON qs.query_id = sm.id
    WHERE sm.session_id = %s
    ORDER BY qs.seq_no ASC
    """
    rows = await rss.query(query, (session_id,))
    citation_ids = {}
    for qid, sid in rows:
        citation_ids.setdefault(qid, []).append(sid)

    return citation_ids


# @with_oa_client(client_name=oa_client_name)
# async def generate_session_title(
#     query: str,
#     *,
#     max_length: int = 20,
#     oaclient: AsyncOpenAI,
# ) -> str:
#     """
#     Generate a session title based on the user query.
# 
#     Arguments:
#         query: The user query.
#         max_length: The maximum length of the title.
# 
#     Returns:
#         The generated session title.
#     """
#     title = query.strip()
#     if len(title) > max_length:
#         system_prompt = (
#             "你是一名助手，需根据用户的查询生成简洁且相关的会话标题。"
#             "请输出能抓住查询核心、字数精炼的标题。"
#         )
#         response = await chat_completion(
#             client=oaclient,
#             model=oa_model_name,
#             prompt=(
#                 f"基于以下用户查询生成一个不超过 {max_length} 字的简洁标题：{query}"
#             ),
#             system_prompt=system_prompt,
#             temperature=0.5,
#         )
#         title = extract_from_chat(response).get("content", "").strip()
#     return title


async def dislike_message(message_id: str, dislikes: int):
    from .. import rss

    await rss.dml(
        "UPDATE session_messages SET dislikes = %s WHERE id = %s",
        (dislikes, message_id),
    )


async def like_message(message_id: str, likes: int):
    from .. import rss

    await rss.dml(
        "UPDATE session_messages SET likes = %s WHERE id = %s", (likes, message_id)
    )


async def update_session_title(session_id: str, title: str):
    from .. import rss

    await rss.dml("UPDATE sessions SET title = %s WHERE id = %s", (title, session_id))


async def delete_session_by_id(session_id: str):
    from .. import rss

    await rss.dml("DELETE FROM sessions WHERE id = %s", (session_id,))


async def pin_session_by_id(session_id: str):
    from .. import rss

    await rss.dml(
        "UPDATE sessions SET created_ts = %s WHERE id = %s",
        (datetime.now(), session_id),
    )


async def next_session_batch(
    user_id: str,
    last_session_id: str | None,
    batch_size: int = 10,
) -> list[tuple]:
    from .. import rss

    query = """
        WITH last_msgs AS (
            SELECT sm.id, sm.session_id, sm.content, sm.created_ts,
                ROW_NUMBER() OVER (
                    PARTITION BY sm.session_id ORDER BY sm.created_ts DESC
                ) AS rn
            FROM session_messages sm
        )
        SELECT
            s.id,
            s.title,
            s.user_id,
            s.created_ts,
            lm.content
        FROM sessions s
        LEFT JOIN last_msgs lm ON lm.session_id = s.id AND lm.rn = 1
        WHERE s.user_id = %s
    """
    params: list[str | int] = [user_id]
    if last_session_id:
        query += " AND s.created_ts < (SELECT created_ts FROM sessions WHERE id = %s)"
        params.append(last_session_id)
    query += " ORDER BY s.created_ts DESC LIMIT %s"
    params.append(batch_size)
    rows = await rss.query(query, tuple(params))

    return rows


async def search_result_batch(results: list[tuple[str, float]]) -> list[tuple]:
    from .. import rss

    if not results:
        return []

    placeholders = ",".join(["%s"] * len(results))
    query = f"""
        WITH last_msgs AS (
            SELECT sm.id, sm.session_id, sm.content, sm.created_ts,
                ROW_NUMBER() OVER (
                    PARTITION BY sm.session_id ORDER BY sm.created_ts DESC
                ) AS rn
            FROM session_messages sm
        )
        SELECT
            s.id,
            s.title,
            s.user_id,
            s.created_ts,
            lm.content
        FROM sessions s
        LEFT JOIN last_msgs lm ON lm.session_id = s.id AND lm.rn = 1
        WHERE s.id IN ({placeholders})
        ORDER BY FIELD(s.id, {placeholders})
    """
    params = [x[0] for x in results] * 2
    rows = await rss.query(query, tuple(params))

    return rows
