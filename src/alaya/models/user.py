from pydantic import BaseModel


class User(BaseModel):
    id: str | None = None
    account: str = "Guest"
    username: str = "访客"
    user_path: str = "访客"
