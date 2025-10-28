from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict
from typing import Any, List

from .base_validator import BaseValidator, ValidationResult
from .types import ValidationIssue

logger = logging.getLogger(__name__)


class AsyncValidator(BaseValidator):
    def __init__(
        self,
        config: Any,
        storage: Any,
        max_concurrency: int | None = None,
        per_task_timeout: float | None = 30.0,
    ) -> None:
        super().__init__(config, storage)
        self._max_concurrency = max_concurrency or min(32, (os.cpu_count() or 4) * 2)
        self._timeout = per_task_timeout

    async def _validate_one_async(self, file_path: str) -> ValidationResult:
        return await asyncio.to_thread(self._validate_one_sync, file_path)

    def _validate_one_sync(self, file_path: str) -> ValidationResult:
        data, errors = self._read_and_parse_file(file_path)
        
        issues: List[ValidationIssue] = []
        for err in errors:
            issues.append(ValidationIssue(
                rule_id="file.parse_error",
                message=err,
                keywords=["parse", "error"]
            ))
        
        registry = None
        if data is None:
            return ValidationResult(
                path=file_path,
                valid=False,
                errors=errors,
                issues=[asdict(issue) for issue in issues],
                registry=None,
                data=None
            )
        
        if isinstance(data, dict):
            rule_issues = self._run_validation_rules(data, file_path)
            issues.extend(rule_issues)
            registry = self._extract_registry(data)
        
        for issue in issues:
            self._build_search_keys(issue, data, registry)
        
        valid = len(issues) == 0
        errors = [issue.message for issue in issues]
        
        return ValidationResult(
            path=file_path,
            valid=valid,
            errors=errors,
            issues=[asdict(issue) for issue in issues],
            registry=registry,
            data=data
        )

    async def validate_file(self, file_path: str) -> ValidationResult:
        try:
            if self._timeout:
                return await asyncio.wait_for(
                    self._validate_one_async(file_path),
                    timeout=self._timeout
                )
            else:
                return await self._validate_one_async(file_path)
        except asyncio.TimeoutError:
            logger.error(f"Timeout validating {file_path}")
            timeout_issue = ValidationIssue(
                rule_id="file.timeout",
                message="TIMEOUT",
                keywords=["timeout", "error"]
            )
            return ValidationResult(
                path=file_path,
                valid=False,
                errors=["TIMEOUT"],
                issues=[asdict(timeout_issue)],
                registry=None,
                data=None
            )
        except Exception as e:
            logger.error(f"Error validating {file_path}: {e}")
            error_issue = ValidationIssue(
                rule_id="file.error",
                message=repr(e),
                keywords=["error"]
            )
            return ValidationResult(
                path=file_path,
                valid=False,
                errors=[repr(e)],
                issues=[asdict(error_issue)],
                registry=None,
                data=None
            )

    async def validate_files(self, file_paths: List[str]) -> List[ValidationResult]:
        sem = asyncio.Semaphore(self._max_concurrency)
        tasks = [asyncio.create_task(self.validate_file(path)) for path in file_paths]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def validate_files_sync(self, file_paths: List[str]) -> List[ValidationResult]:
        return asyncio.run(self.validate_files(file_paths))