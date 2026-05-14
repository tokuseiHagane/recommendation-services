"""VkParser Dependency Injection Providers."""

from dishka import Provider, Scope, provide

from src.Containers.AppSection.VkParser.Actions.CheckGroupsExistAction import CheckGroupsExistAction
from src.Containers.AppSection.VkParser.Actions.GetGroupByIdAction import GetGroupByIdAction
from src.Containers.AppSection.VkParser.Actions.GetGroupPostsAction import GetGroupPostsAction
from src.Containers.AppSection.VkParser.Actions.ListGroupsAction import ListGroupsAction
from src.Containers.AppSection.VkParser.Actions.ParseVkDataAction import ParseVkDataAction
from src.Containers.AppSection.VkParser.Actions.SearchVkAction import SearchVkAction
from src.Containers.AppSection.VkParser.Tasks.CacheCheckTask import CacheCheckTask
from src.Containers.AppSection.VkParser.Tasks.FetchVkWallTask import FetchVkWallTask
from src.Containers.AppSection.VkParser.Tasks.FindGroupByIdTask import FindGroupByIdTask
from src.Containers.AppSection.VkParser.Tasks.FindGroupsTask import FindGroupsTask
from src.Containers.AppSection.VkParser.Tasks.FindPostsTask import FindPostsTask
from src.Containers.AppSection.VkParser.Tasks.GetVkTokenTask import GetVkTokenTask
from src.Containers.AppSection.VkParser.Tasks.GroupsExistTask import GroupsExistTask
from src.Containers.AppSection.VkParser.Tasks.PublishToKafkaTask import PublishToKafkaTask
from src.Containers.AppSection.VkParser.Tasks.SaveParsedDataTask import SaveParsedDataTask
from src.Containers.AppSection.VkParser.Tasks.SearchVkTask import SearchVkTask
from src.Containers.AppSection.VkParser.Tasks.VerifyAuthJwtTask import VerifyAuthJwtTask
from src.Ship.Configs.App import AppSettings
from src.Ship.Core.AuthServiceClient import AuthServiceClient
from src.Ship.Core.JwtVerifier import JwtVerifier
from src.Ship.Core.TokenStorage import TokenStorage


class VkParserProvider(Provider):
    """Provider for VkParser container dependencies."""

    # --- Tasks ---

    @provide(scope=Scope.REQUEST)
    def provide_fetch_vk_wall_task(self) -> FetchVkWallTask:
        return FetchVkWallTask()

    @provide(scope=Scope.REQUEST)
    def provide_search_vk_task(self) -> SearchVkTask:
        return SearchVkTask()

    @provide(scope=Scope.REQUEST)
    def provide_get_vk_token_task(
        self,
        settings: AppSettings,
        auth_service_client: AuthServiceClient,
        token_storage: TokenStorage,
    ) -> GetVkTokenTask:
        return GetVkTokenTask(
            settings=settings,
            auth_service_client=auth_service_client,
            token_storage=token_storage,
        )

    @provide(scope=Scope.REQUEST)
    def provide_verify_auth_jwt_task(self, jwt_verifier: JwtVerifier) -> VerifyAuthJwtTask:
        return VerifyAuthJwtTask(jwt_verifier=jwt_verifier)

    @provide(scope=Scope.REQUEST)
    def provide_cache_check_task(self) -> CacheCheckTask:
        return CacheCheckTask()

    @provide(scope=Scope.REQUEST)
    def provide_save_parsed_data_task(self) -> SaveParsedDataTask:
        return SaveParsedDataTask()

    @provide(scope=Scope.REQUEST)
    def provide_publish_to_kafka_task(self) -> PublishToKafkaTask:
        return PublishToKafkaTask()

    @provide(scope=Scope.REQUEST)
    def provide_find_groups_task(self) -> FindGroupsTask:
        return FindGroupsTask()

    @provide(scope=Scope.REQUEST)
    def provide_find_posts_task(self) -> FindPostsTask:
        return FindPostsTask()

    @provide(scope=Scope.REQUEST)
    def provide_find_group_by_id_task(self) -> FindGroupByIdTask:
        return FindGroupByIdTask()

    @provide(scope=Scope.REQUEST)
    def provide_groups_exist_task(self) -> GroupsExistTask:
        return GroupsExistTask()

    # --- Actions ---

    @provide(scope=Scope.REQUEST)
    def provide_parse_vk_data_action(
        self,
        fetch_vk_wall_task: FetchVkWallTask,
        cache_check_task: CacheCheckTask,
        publish_to_kafka_task: PublishToKafkaTask,
        save_parsed_data_task: SaveParsedDataTask,
        find_groups_task: FindGroupsTask,
        find_posts_task: FindPostsTask,
        settings: AppSettings,
    ) -> ParseVkDataAction:
        return ParseVkDataAction(
            fetch_vk_wall_task=fetch_vk_wall_task,
            cache_check_task=cache_check_task,
            publish_to_kafka_task=publish_to_kafka_task,
            save_parsed_data_task=save_parsed_data_task,
            find_groups_task=find_groups_task,
            find_posts_task=find_posts_task,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def provide_search_vk_action(self, search_vk_task: SearchVkTask) -> SearchVkAction:
        return SearchVkAction(search_vk_task=search_vk_task)

    @provide(scope=Scope.REQUEST)
    def provide_list_groups_action(self, find_groups_task: FindGroupsTask) -> ListGroupsAction:
        return ListGroupsAction(find_groups_task=find_groups_task)

    @provide(scope=Scope.REQUEST)
    def provide_get_group_posts_action(self, find_posts_task: FindPostsTask) -> GetGroupPostsAction:
        return GetGroupPostsAction(find_posts_task=find_posts_task)

    @provide(scope=Scope.REQUEST)
    def provide_get_group_by_id_action(
        self, find_group_by_id_task: FindGroupByIdTask
    ) -> GetGroupByIdAction:
        return GetGroupByIdAction(find_group_by_id_task=find_group_by_id_task)

    @provide(scope=Scope.REQUEST)
    def provide_check_groups_exist_action(
        self, groups_exist_task: GroupsExistTask
    ) -> CheckGroupsExistAction:
        return CheckGroupsExistAction(groups_exist_task=groups_exist_task)
