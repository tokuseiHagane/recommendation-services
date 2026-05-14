from __future__ import annotations

import asyncio
from typing import Any

from aiovk import API
from aiovk.pools import (
    AsyncResult as AiovkAsyncResult,
)
from aiovk.pools import (
    AsyncVkExecuteRequestPool,
    VkExecuteMethodsPool,
    chunks,
)

from src.VkParser.logging_utils import get_logger

logger = get_logger(__name__)


class MetaAsyncResult(AiovkAsyncResult):
    def __init__(self):
        super().__init__()
        self._meta = None

    @property
    def meta(self):
        return self._meta

    @meta.setter
    def meta(self, value):
        self._meta = value


class AdvancedExecutePool(AsyncVkExecuteRequestPool):
    """
    Расширение execute-пула VK API.

    Добавляет:
        - автоматическое уменьшение размера чанка при ошибке 13
        - повторную отправку запросов при ошибках
        - поддержку meta-информации для каждого запроса
    """

    def __init__(self, api: API, call_number_per_request: int = 25):
        super().__init__(call_number_per_request)
        self.api = api
        self.token: str = api._session.access_token

    async def __aexit__(self, *args, **kwargs): ...

    async def _execute(self) -> None:
        executed_pools = []

        async def handle_error(error, methods_pool, chunk_size, executed_pools):
            error_code = error.get("error_code", None)
            if error_code == 13:
                logger.warning("vk api error 13: reducing chunk size, chunk_size=%d", chunk_size)
                await create_and_add_chunks(methods_pool, chunk_size // 2, executed_pools)
            else:
                logger.warning("vk api error: retrying with same chunk size, error=%s", error)
                await create_and_add_chunks(methods_pool, chunk_size, executed_pools)

        async def create_and_add_chunks(calls, chunk_size, pools_list):
            for methods_pool in chunks(calls, chunk_size):

                async def execute_with_methods_pool(methods_pool):
                    try:
                        await VkExecuteMethodsPool(methods_pool).execute(self.api)
                        return None, methods_pool, chunk_size
                    except Exception as e:
                        # print(e)
                        error = e.args[0] if e.args else {}
                        return error, methods_pool, chunk_size

                pools_list.append(execute_with_methods_pool(methods_pool))

        for _, calls in self.pool.items():
            await create_and_add_chunks(calls, self.call_number_per_request, executed_pools)

        while executed_pools:
            res = await asyncio.gather(*executed_pools, return_exceptions=True)
            errors = [x for x in res if x[0]]

            next_executed_pools = []
            for error, methods_pool, chunk_size in errors:
                logger.warning("handling error: %s", error)
                await handle_error(error, methods_pool, chunk_size, next_executed_pools)

            executed_pools = next_executed_pools

    def add_call(self, method: str, method_args: dict[str, Any] | None = None) -> MetaAsyncResult:
        return super().add_call(method, self.token, method_args)

    async def add_calls_with_results(self, **named_method_arg_pairs_list):
        all_results: dict[str, list[MetaAsyncResult]] = {name: [] for name in named_method_arg_pairs_list}
        errors: dict[str, list] = {name: [] for name in named_method_arg_pairs_list}

        for name, method_arg_pairs in named_method_arg_pairs_list.items():
            for method, method_args, *meta in method_arg_pairs:
                result: MetaAsyncResult = self.add_call(method, method_args)
                result.meta = meta[0] if meta else None
                all_results[name].append(result)

        await self._execute()
        self.pool.clear()

        ret_res: dict[str, list] = {}

        for name, results in all_results.items():
            ret_res.setdefault(name, [])
            for result in results:
                if not result.ok:
                    error_info = (result.error, result.meta) if result.meta else (result.error,)
                    errors[name].append(error_info)
                    continue
                if result.meta:
                    ret_res[name].append((result.result, result.meta))
                else:
                    ret_res[name].append(result.result)

        return ret_res, errors
