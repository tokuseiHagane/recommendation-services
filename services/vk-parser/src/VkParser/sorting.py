from __future__ import annotations

from typing import Any


def default_sort_params() -> dict[str, dict[str, Any]]:
    return {
        "date": {"priority": 1, "reverse": False},
        "engagement_rate": {"priority": 1, "reverse": True},
        "views": {"priority": 1, "reverse": True},
        "comments": {"priority": 1, "reverse": True},
        "reposts": {"priority": 1, "reverse": True},
    }


def sort_posts(
    posts: list[dict[str, Any]],
    sort_params: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    effective_sort_params = sort_params or default_sort_params()

    def get_score(post: dict[str, Any]) -> int | float:
        score = 0
        for param, param_data in effective_sort_params.items():
            priority = int(param_data["priority"])
            reverse = bool(param_data["reverse"])

            if param == "date":
                value = post["date"]
            elif param == "engagement_rate":
                value = (
                    post.get("likes", {}).get("count", 0)
                    + post.get("reposts", {}).get("count", 0)
                    + post.get("comments", {}).get("count", 0)
                )
            elif param in {"views", "comments", "reposts"}:
                value = post.get(param, {}).get("count", 0)
            else:
                raise ValueError(f"Unknown sort_by value: {param}")

            if reverse:
                value = -value

            score += priority * value

        return score

    return sorted(posts, key=get_score, reverse=True)
