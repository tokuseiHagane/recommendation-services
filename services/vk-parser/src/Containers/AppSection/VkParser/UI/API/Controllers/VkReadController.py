"""VK Read API Controllers — read cached groups and posts from DB."""

from datetime import UTC, date, datetime, time

from dishka.integrations.base import FromDishka
from dishka.integrations.litestar import inject
from litestar import Request, get
from litestar.exceptions import NotFoundException, ValidationException
from litestar.params import Parameter
from litestar.response import Response

from src.Containers.AppSection.VkParser.Actions.CheckGroupsExistAction import CheckGroupsExistAction
from src.Containers.AppSection.VkParser.Actions.GetGroupByIdAction import GetGroupByIdAction
from src.Containers.AppSection.VkParser.Actions.GetGroupPostsAction import GetGroupPostsAction
from src.Containers.AppSection.VkParser.Actions.ListGroupsAction import ListGroupsAction
from src.Containers.AppSection.VkParser.Tasks.FindGroupsTask import FindGroupsInput
from src.Containers.AppSection.VkParser.Tasks.FindPostsTask import FindPostsInput
from src.Ship.Parents.Controller import BaseController


def _parse_date_boundary(raw: str | None, *, field: str, end_of_day: bool) -> datetime | None:
    """Parse ``start_date`` / ``end_date`` query params tolerantly.

    Accepts both ``YYYY-MM-DD`` (which the frontend sends via
    ``toISOString().slice(0, 10)``) and full RFC3339 datetimes. Date-only
    values are widened to the full UTC day — ``start_date`` to 00:00:00
    and ``end_date`` to 23:59:59.999999 — so ``end_date`` inclusively
    covers the whole requested day instead of cutting off at midnight.
    """
    if raw is None or raw == "":
        return None

    try:
        parsed_date = date.fromisoformat(raw)
    except ValueError:
        parsed_date = None

    if parsed_date is not None:
        boundary = time.max if end_of_day else time.min
        return datetime.combine(parsed_date, boundary, tzinfo=UTC)

    try:
        parsed_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationException(
            detail=(
                f"Invalid {field!r}: expected YYYY-MM-DD or RFC3339 datetime, "
                f"got {raw!r}."
            ),
        ) from exc

    if parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=UTC)
    return parsed_dt


def _parse_ids_csv(raw: str | None) -> list[int]:
    if not raw:
        return []
    parsed: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            parsed.append(int(chunk))
        except ValueError:
            continue
    return parsed


class VkGroupsController(BaseController):
    """Read API for cached VK groups."""

    path = "/groups"

    @get()
    @inject
    async def list_groups(
        self,
        request: Request,
        action: FromDishka[ListGroupsAction],
        q: str | None = Parameter(query="q", default=None),
        screen_name: str | None = Parameter(query="screen_name", default=None),
        limit: int = Parameter(query="limit", default=50, ge=1, le=200),
        offset: int = Parameter(query="offset", default=0, ge=0),
    ) -> Response:
        self.log_request(request)
        # `q` is the new substring search (§3.1). `screen_name` kept for
        # backwards compatibility: if only `screen_name` is passed we treat it
        # as exact match (as before) — existing callers keep working.
        result = await action.execute(
            FindGroupsInput(
                screen_name=screen_name,
                q=q,
                limit=limit,
                offset=offset,
            )
        )
        return Response(content={"status": "success", "data": result, "count": len(result)})

    @get("/exists")
    @inject
    async def groups_exists(
        self,
        request: Request,
        action: FromDishka[CheckGroupsExistAction],
        ids: str = Parameter(query="ids", description="Comma-separated VK group ids"),
    ) -> Response:
        self.log_request(request, ids=ids)
        parsed_ids = _parse_ids_csv(ids)
        mapping = await action.execute(parsed_ids)
        # Keys become strings in JSON anyway — emit them as strings up front
        # so clients don't have to deal with int-vs-string flip-flops.
        serialized = {str(gid): present for gid, present in mapping.items()}
        return Response(content={"status": "success", "data": serialized, "count": len(serialized)})

    @get("/{group_id:int}")
    @inject
    async def get_group(
        self,
        request: Request,
        group_id: int,
        action: FromDishka[GetGroupByIdAction],
    ) -> Response:
        self.log_request(request, group_id=group_id)
        group = await action.execute(group_id)
        if group is None:
            raise NotFoundException(detail=f"Group {group_id} not found in cache")
        return Response(content={"status": "success", "data": group})


class VkPostsController(BaseController):
    """Read API for cached VK posts."""

    path = "/groups/{group_id:int}/posts"

    @get()
    @inject
    async def list_posts(
        self,
        request: Request,
        group_id: int,
        action: FromDishka[GetGroupPostsAction],
        start_date: str | None = Parameter(query="start_date", default=None),
        end_date: str | None = Parameter(query="end_date", default=None),
        limit: int = Parameter(query="limit", default=50, ge=1, le=200),
        offset: int = Parameter(query="offset", default=0, ge=0),
    ) -> Response:
        self.log_request(request, group_id=group_id)
        start_dt = _parse_date_boundary(start_date, field="start_date", end_of_day=False)
        end_dt = _parse_date_boundary(end_date, field="end_date", end_of_day=True)
        result = await action.execute(
            FindPostsInput(
                group_id=group_id,
                start_date=start_dt,
                end_date=end_dt,
                limit=limit,
                offset=offset,
            )
        )
        return Response(content={"status": "success", "data": result, "count": len(result)})
