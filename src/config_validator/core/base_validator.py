from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List

import yaml

from ..storage.local_strategy import LocalStrategy
from .config import ValidationConfig
from .rules_loader import load_rules
from .types import ValidationIssue

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    path: str
    valid: bool
    errors: List[str]
    issues: List[Dict[str, Any]]
    registry: str | None
    data: Dict[str, Any] | None


class BaseValidator(ABC):
    def __init__(self, config: ValidationConfig, storage: LocalStrategy) -> None:
        self.config = config
        self.storage = storage
        self._validators: List[Callable] | None = None
    
    @property
    def validators(self) -> List[Callable]:
        if self._validators is None:
            self._validators = load_rules()
        return self._validators
    
    def _read_and_parse_file(self, file_path: str) -> tuple[Dict[str, Any] | None, List[str]]:
        errors: List[str] = []
        
        try:
            content = self.storage.read_file(file_path)
        except Exception as e:
            return None, [f"Failed to read file {file_path}: {e}"]
        
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            return None, [f"YAML parse error in {file_path}: {e}"]
        except Exception as e:
            return None, [f"Error parsing YAML from {file_path}: {e}"]
        
        if isinstance(data, list):
            d = {}
            for x in data:
                if isinstance(x, dict):
                    d.update(x)
            data = d
        
        return data, errors
    
    def _extract_registry(self, data: Dict[str, Any]) -> str | None:
        img = data.get("image")
        if isinstance(img, str):
            import re
            m = re.compile(self.config.image_pattern).match(img)
            if m:
                return m.group("registry")
        return None
    
    def _build_search_keys(self, issue: ValidationIssue, data: Dict[str, Any] | None, registry: str | None) -> None:
        keys = [f"rule:{issue.rule_id}"]
        
        for k in issue.keywords:
            keys.append(f"keyword:{k}")
        
        if data and isinstance(data, dict):
            svc = data.get("service")
            if svc:
                keys.append(f"service:{svc}")
        
        if registry:
            keys.append(f"registry:{registry}")
        
        issue.search_keys = sorted(set(keys))
    
    def _run_validation_rules(self, data: Dict[str, Any], file_path: str) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        
        for validator_func in self.validators:
            try:
                rule_issues = validator_func(data, self.config)
                issues.extend(rule_issues)
            except Exception as rule_exc:
                logger.exception(f"Validator {validator_func.__qualname__} error")
                issues.append(ValidationIssue(
                    rule_id=f"{validator_func.__qualname__}.error",
                    message=str(rule_exc),
                    keywords=["error"]
                ))
        
        return issues
    
    @abstractmethod
    def validate_file(self, file_path: str) -> ValidationResult:
        pass
    
    @abstractmethod
    def validate_files(self, file_paths: List[str]) -> List[ValidationResult]:
        pass
