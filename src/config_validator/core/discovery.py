from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..storage.local_strategy import LocalStrategy


class Discovery:
    def __init__(self, root: Path, storage_strategy: LocalStrategy) -> None:
        self.root = root
        self._storage_strategy = storage_strategy

    def discover_yaml_files(self, root: Path) -> Iterable[Path]:
        return self._storage_strategy.get_yaml_files(root)
 