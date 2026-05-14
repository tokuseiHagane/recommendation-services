"""Base Task class according to Porto architecture."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import logfire

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Task(ABC, Generic[InputT, OutputT]):
    """Base Task class.

    Tasks are atomic operations that can be reused across Actions.
    They should be focused on a single responsibility.
    """

    @abstractmethod
    async def run(self, data: InputT) -> OutputT:
        """Execute the task.

        Args:
            data: Input data for the task

        Returns:
            Output data from the task
        """
        raise NotImplementedError

    async def execute(self, data: InputT) -> OutputT:
        """Execute task with logging.

        Args:
            data: Input data for the task

        Returns:
            Output data from the task
        """
        task_name = self.__class__.__name__

        with logfire.span(
            f"⚙️ {task_name}", task=task_name, input_type=type(data).__name__ if data is not None else "None"
        ):
            try:
                result = await self.run(data)

                logfire.debug(
                    f"✓ {task_name} completed",
                    task=task_name,
                )

                return result

            except Exception as e:
                logfire.error(
                    f"✗ {task_name} failed",
                    task=task_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise
