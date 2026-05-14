"""Base Action class according to Porto architecture."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import logfire

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Action(ABC, Generic[InputT, OutputT]):
    """Base Action class.

    Actions represent the Use Cases of the Application.
    Every Action should be responsible for performing a single use case.
    """

    @abstractmethod
    async def run(self, data: InputT) -> OutputT:
        """Execute the action.

        Args:
            data: Input data for the action

        Returns:
            Output data from the action
        """
        raise NotImplementedError

    async def execute(self, data: InputT) -> OutputT:
        """Execute action with logging and tracing.

        Args:
            data: Input data for the action

        Returns:
            Output data from the action
        """
        action_name = self.__class__.__name__

        with logfire.span(
            f"🚀 {action_name}", action=action_name, input_type=type(data).__name__ if data is not None else "None"
        ):
            try:
                logfire.info(f"▶️ Starting {action_name}", action=action_name)
                result = await self.run(data)

                logfire.info(
                    f"✅ {action_name} completed successfully",
                    action=action_name,
                    output_type=type(result).__name__ if result is not None else "None",
                )

                return result

            except Exception as e:
                logfire.error(
                    f"❌ {action_name} failed",
                    action=action_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise
