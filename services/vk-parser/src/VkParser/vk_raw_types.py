from typing import Any

# Pydantic on Python <3.12 requires TypedDict from typing_extensions
# NotRequired is also provided by typing_extensions when used for backwards
# compatibility. This prevents `PydanticUserError` during model parsing.
from typing_extensions import TypedDict


class VkCountDict(TypedDict, total=False):
    count: int


class VkViewsDict(TypedDict, total=False):
    count: int


class VkWallPostRaw(TypedDict, total=False):
    id: int
    owner_id: int
    date: int
    edited: int
    text: str
    likes: VkCountDict
    reposts: VkCountDict
    comments: VkCountDict
    views: VkViewsDict


class VkGroupInfoRaw(TypedDict, total=False):
    id: int
    name: str
    screen_name: str
    members_count: int

    # поля, которые добавляемые уже в ходе пайплайна
    posts_count: int
    posts: list[VkWallPostRaw]


class VkUserInfoRaw(TypedDict, total=False):
    domain: str
    counters: dict[str, Any]
