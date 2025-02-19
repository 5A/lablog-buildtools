from typing import Optional
from pydantic import BaseModel


class PostMetadata(BaseModel):
    title: str
    author: str
    email: str
    abstract: str
    root: str
    timestamp: Optional[float] = None
    datetime: Optional[str] = None
    catagory: Optional[str] = None
    tags: Optional[list[str]] = None
    post_id: Optional[str] = None


class PageMetadata(BaseModel):
    title: str
    root: str
