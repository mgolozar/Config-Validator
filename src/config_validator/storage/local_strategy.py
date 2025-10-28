import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable

logger = logging.getLogger(__name__)


class LocalStrategy:
    EXCLUDED_DIRS = {'.git', 'node_modules', '.idea', '.venv', '__pycache__'}
    EXCLUDED_EXTS = {'.zip', '.tar', '.gz', '.rar'}
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.validate_config()
        self.base_path = Path(self.config.get("base_path", "."))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def validate_config(self) -> bool:
        base_path = self.config.get("base_path")
        if not base_path:
            raise ValueError("LocalStrategy requires 'base_path' in configuration")
        return True
    
    @staticmethod
    def fast_walk(root: Path) -> Iterable[Path]:
        stack = [root]
        while stack:
            d = stack.pop()
            try:
                with os.scandir(d) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name in LocalStrategy.EXCLUDED_DIRS:
                                continue
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            p = Path(entry.path)
                            if p.suffix.lower() not in LocalStrategy.EXCLUDED_EXTS:
                                yield p
            except (PermissionError, FileNotFoundError):
                continue
    
    @staticmethod
    def get_yaml_files(root: Path) -> Iterable[Path]:
        for p in LocalStrategy.fast_walk(root):
            if p.suffix.lower() in {'.yml', '.yaml'}:
                yield p.resolve()
    
    def read_file(self, remote_path: str) -> str:
        file_path = Path(remote_path)
        with file_path.open("r", encoding="utf-8") as f:
            return f.read()
