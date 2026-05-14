from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.VkParser.config import get_project_root


@dataclass(frozen=True)
class OutputPaths:
    run_dir: Path
    data_json: Path


def get_output_paths(base_dirname: str = "outputs") -> OutputPaths:
    """
    Создаёт папку запуска вида:

    outputs/2026-02-27_15-42-10/
        └── data.json
    """
    project_root = get_project_root()

    base_dir = project_root / base_dirname
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)

    return OutputPaths(
        run_dir=run_dir,
        data_json=run_dir / "data.json",
    )
