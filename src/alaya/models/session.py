from pydantic import BaseModel
from datetime import datetime
from openai.types.chat import ChatCompletionRole


class Message(BaseModel):
    id: str
    session_id: str
    seq_no: int
    role: ChatCompletionRole
    content: str
    created_ts: datetime
    likes: int = 0
    dislikes: int = 0
    pair_id: str


class Session(BaseModel):
    id: str
    title: str
    created_ts: datetime
    user_id: str
