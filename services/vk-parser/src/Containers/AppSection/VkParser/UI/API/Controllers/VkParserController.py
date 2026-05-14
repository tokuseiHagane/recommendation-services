"""VK Parser API Controllers with Bearer JWT authentication."""

import logfire
from dishka.integrations.base import FromDishka
from dishka.integrations.litestar import inject
from litestar import Request, get, post
from litestar.response import Response

from src.Containers.AppSection.VkParser.Actions.ParseVkDataAction import ParseVkDataAction
from src.Containers.AppSection.VkParser.Actions.SearchVkAction import SearchVkAction
from src.Containers.AppSection.VkParser.Data.Dto import VkParseRequest
from src.Containers.AppSection.VkParser.Exceptions import VkAuthenticationError
from src.Containers.AppSection.VkParser.Tasks.GetVkTokenTask import GetVkTokenInput, GetVkTokenTask
from src.Containers.AppSection.VkParser.Tasks.VerifyAuthJwtTask import VerifyAuthJwtTask
from src.Ship.Configs.App import AppSettings
from src.Ship.Parents.Controller import BaseController

AUTH_COOKIE_NAME = "auth_token"


def extract_auth_token(
    request: Request,
    settings: AppSettings,
) -> tuple[str, str]:
    """Extract bearer token with optional temporary cookie fallback."""
    authorization_header = request.headers.get("Authorization")
    if authorization_header:
        scheme, _, raw_token = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not raw_token.strip():
            raise VkAuthenticationError(
                message="Invalid Authorization header.",
                details={"error": "invalid_authorization_header"},
            )
        return raw_token.strip(), "bearer"

    if settings.auth_enable_legacy_cookie_fallback:
        raw_token = request.cookies.get(AUTH_COOKIE_NAME)
        if raw_token:
            logfire.warning("Using legacy auth cookie fallback", cookie_name=AUTH_COOKIE_NAME)
            return raw_token, "legacy_cookie"

    raise VkAuthenticationError(
        message="Authentication required. Send Authorization: Bearer <jwt>.",
        details={
            "error": "missing_bearer_token",
            "legacy_cookie_fallback_enabled": settings.auth_enable_legacy_cookie_fallback,
        },
    )


async def resolve_vk_auth_context(
    request: Request,
    settings: AppSettings,
    verify_auth_jwt_task: VerifyAuthJwtTask,
    get_vk_token_task: GetVkTokenTask,
) -> tuple[str, str]:
    """Resolve verified auth user context and VK token for parser requests."""
    raw_token, auth_source = extract_auth_token(request, settings)
    verified = await verify_auth_jwt_task.execute(raw_token)
    vk_token = await get_vk_token_task.execute(
        GetVkTokenInput(
            auth_user_id=verified.auth_user_id,
            jwt_token=raw_token,
        )
    )
    logfire.debug(
        "Resolved VK auth context",
        auth_user_id=verified.auth_user_id,
        auth_source=auth_source,
    )
    return vk_token, verified.auth_user_id


class VkParserController(BaseController):
    """VK Parser API Controller — parse VK profiles, groups and posts."""

    path = "/parse/vk"

    @post()
    @inject
    async def parse_vk_data(
        self,
        request: Request,
        data: VkParseRequest,
        action: FromDishka[ParseVkDataAction],
        settings: FromDishka[AppSettings],
        verify_auth_jwt_task: FromDishka[VerifyAuthJwtTask],
        get_vk_token_task: FromDishka[GetVkTokenTask],
    ) -> Response:
        self.log_request(request)
        vk_token, auth_user_id = await resolve_vk_auth_context(
            request=request,
            settings=settings,
            verify_auth_jwt_task=verify_auth_jwt_task,
            get_vk_token_task=get_vk_token_task,
        )
        self.log_action_call("ParseVkDataAction", links_count=len(data.links), auth_user_id=auth_user_id)

        result = await action.execute((vk_token, data))

        self.log_response(request, status=200, domains_count=len(result))
        return Response(
            content={"status": "success", "data": result, "domains_count": len(result)},
        )


class VkSearchController(BaseController):
    """VK Search API Controller — search VK profiles and groups."""

    path = "/search/vk"

    @get()
    @inject
    async def search_vk(
        self,
        request: Request,
        q: str,
        action: FromDishka[SearchVkAction],
        settings: FromDishka[AppSettings],
        verify_auth_jwt_task: FromDishka[VerifyAuthJwtTask],
        get_vk_token_task: FromDishka[GetVkTokenTask],
    ) -> Response:
        self.log_request(request, query=q)
        vk_token, auth_user_id = await resolve_vk_auth_context(
            request=request,
            settings=settings,
            verify_auth_jwt_task=verify_auth_jwt_task,
            get_vk_token_task=get_vk_token_task,
        )
        self.log_action_call("SearchVkAction", query=q, auth_user_id=auth_user_id)

        result = await action.execute((vk_token, q))
        items_count = len(result.get("items", [])) if result else 0

        self.log_response(request, status=200, results_count=items_count)
        return Response(
            content={"status": "success", "data": result, "count": items_count},
        )


class VkHealthController(BaseController):
    """Health check controller."""

    path = "/health"

    @get()
    @inject
    async def health_check(
        self,
        request: Request,
        settings: FromDishka[AppSettings],
        verify_auth_jwt_task: FromDishka[VerifyAuthJwtTask],
        get_vk_token_task: FromDishka[GetVkTokenTask],
    ) -> Response:
        self.log_request(request)

        try:
            vk_token, auth_user_id = await resolve_vk_auth_context(
                request=request,
                settings=settings,
                verify_auth_jwt_task=verify_auth_jwt_task,
                get_vk_token_task=get_vk_token_task,
            )
            authenticated = True
            has_vk_token = bool(vk_token)
        except VkAuthenticationError:
            authenticated = False
            has_vk_token = False
            auth_user_id = None

        return Response(
            content={
                "status": "healthy",
                "service": "vk-parser-service",
                "authenticated": authenticated,
                "has_vk_token": has_vk_token,
                "auth_user_id": auth_user_id,
            },
        )
