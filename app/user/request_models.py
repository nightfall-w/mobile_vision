"""
@FileName：request_models.py
@Description：
@Author：baojun.wang
@Time：2025/10/31 14:04
"""
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class PaginationRequestModel(BaseModel):
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页大小")

    @model_validator(mode="after")
    def check_pagination(self):
        if self.page_num < 1 or self.page_size < 1:
            raise ValueError("分页参数必须大于等于1")
        return self


class UserCreate(BaseModel):
    username: str
    email: str
    nickname: str
    password: str


class UserDetail(BaseModel):
    id: int


class UserLogin(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    is_deleted: bool

    class Config:
        from_attributes = True


class UserList(PaginationRequestModel):
    search: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class CurrentUser:
    def __init__(self, _id: int = None, username: str = None, email: str = None, nickname: str = None,
                 is_deleted: bool = False, new_token=None):
        self.id = _id
        self.username = username
        self.email = email
        self.nickname = nickname
        self.is_deleted = is_deleted
        self.new_token = new_token
