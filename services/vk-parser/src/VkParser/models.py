from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class VkMethodsUsers(StrEnum):
    GET = "users.get"
    GET_FOLLOWERS = "users.getFollowers"


class VkMethodsWall(StrEnum):
    GET = "wall.get"
    GET_COMMENTS = "wall.getComments"


class VkMethodsGroups(StrEnum):
    GET_BY_ID = "groups.getById"
    GET_MEMBERS = "groups.getMembers"


class GroupRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    screen_name: str | None = None
    members_count: int | None = None
    photo_url: str | None = None
    cover_url: str | None = None


class PostRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    len_message: int
    repost_count: int
    view_count: int
    comments_count: int
    message_timestamp: datetime | None = None
    edit_date: datetime | None = None
    reactions_count: int
    id_groups: int | None = None


class VkData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    groups: list[GroupRow]
    posts: list[PostRow]
