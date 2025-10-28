from __future__ import annotations

import json
import logging
import os
import threading
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional

import yaml

from .base_validator import BaseValidator, ValidationResult
from .config import load_validation_config
from .discovery import Discovery
from .async_validator import AsyncValidator
from ..storage.strategy_loader import load_storage_strategy

logger = logging.getLogger(__name__)


def write_file_event(stream_fp, event: dict) -> None:
    """Write a file event as a single compact JSON line to the stream."""
    line = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
    stream_fp.write(line + '\n')
    stream_fp.flush()
    os.fsync(stream_fp.fileno())


class ValidationService:
    def __init__(
        self,
        root_path: Path,
        report_path: Path,
        config_path: Path | None = None,
        storage_config_path: Path | None = None,
        replicas_min: int | None = None,
        replicas_max: int | None = None,
        max_concurrency: int | None = None,
        batch_size: int = 100,
    ) -> None:
        self.root_path = root_path
        self.report_path = report_path
        self.config_path = config_path
        self.storage_config_path = storage_config_path
        self.replicas_min = replicas_min
        self.replicas_max = replicas_max
        self.max_concurrency = max_concurrency
        self.batch_size = batch_size

        self._config = None
        self._storage_strategy = None
        self._discovery = None
        self._validator: BaseValidator | None = None
        
        self._write_lock = threading.Lock()

    def _load_config(self) -> None:
        if self._config is None:
            self._config = load_validation_config(self.config_path)

            if self.replicas_min is not None:
                self._config.replicas_min = self.replicas_min
            if self.replicas_max is not None:
                self._config.replicas_max = self.replicas_max

    def _load_storage_strategy(self) -> None:
        if self._storage_strategy is None:
            if self.storage_config_path is None or not self.storage_config_path.exists():
                raise FileNotFoundError(f"Storage config file not found: {self.storage_config_path}")

            storage_config = self.load_yaml(self.storage_config_path)
            self._storage_strategy = load_storage_strategy(storage_config)

    def _setup_discovery(self) -> None:
        if self._discovery is None:
            self._load_storage_strategy()
            self._discovery = Discovery(self.root_path, self._storage_strategy)

    def _setup_validator(self) -> None:
        if self._validator is None:
            self._load_config()
            self._load_storage_strategy()
            
            self._validator = AsyncValidator(
                config=self._config,
                storage=self._storage_strategy,
                max_concurrency=self.max_concurrency
            )

    @staticmethod
    def load_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def discover_files(self) -> Iterable[Path]:
        self._setup_discovery()
        return self._discovery.discover_yaml_files(self.root_path)

    def validate_files(self, files: Iterable[Path]) -> List[ValidationResult]:
        self._setup_validator()
        
        all_results = []
        batch = []
        batch_count = 0
        total_files = 0
        
        for file_path in files:
            batch.append(file_path)
            total_files += 1
            
            if len(batch) >= self.batch_size:
                batch_count += 1
                file_paths = [str(f) for f in batch]
                
                if total_files > 1000:
                    logger.info(f"Processing batch {batch_count} ({len(batch)} files, {total_files} total)...")
                
                batch_results = self._validator.validate_files_sync(file_paths)
                all_results.extend(batch_results)
                batch = []
        
        if batch:
            batch_count += 1
            file_paths = [str(f) for f in batch]
            if total_files > 1000:
                logger.info(f"Processing final batch {batch_count} ({len(batch)} files, {total_files} total)...")
            
            batch_results = self._validator.validate_files_sync(file_paths)
            all_results.extend(batch_results)
        
        if total_files == 0:
            logger.warning("No files to validate")
        elif total_files > 1000:
            logger.info(f"Completed validation of {total_files} files in {batch_count} batches")
        
        return all_results

    def _create_file_event(self, result: ValidationResult, run_id: str, ts: str) -> dict[str, Any]:
        service = ""
        if result.data and isinstance(result.data, dict):
            service = result.data.get("service") or result.data.get("name") or ""
        
        sample_error = ""
        if result.errors:
            sample_error = result.errors[0][:200]
        elif result.issues and result.issues[0].get("message"):
            sample_error = result.issues[0]["message"][:200]
        
        sha256 = ""
        if result.data:
            try:
                payload = json.dumps(result.data, sort_keys=True, separators=(",", ":"))
                sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            except Exception:
                sha256 = ""
        
        event: dict[str, Any] = {
            "type": "file",
            "ts": ts,
            "run_id": run_id,
            "path": result.path,
            "registry": result.registry or "",
            "service": service,
            "valid": result.valid,
            "error_count": len(result.errors) + len(result.issues),
            "rule_ids": [],
            "keywords": [],
            "sample_error": sample_error,
            "sha256": sha256,
        }
        
        if result.issues:
            rule_ids = set()
            keywords = set()
            
            for issue in result.issues[:8]:
                rule_id = issue.get("rule_id")
                if rule_id:
                    rule_ids.add(rule_id)
                
                for keyword in issue.get("keywords", [])[:4]:
                    keywords.add(keyword)
            
            event["rule_ids"] = sorted(list(rule_ids))[:8]
            event["keywords"] = sorted(list(keywords))[:8]
        
        return event
    
    def stream_to_ndjson(self, results: List[ValidationResult]) -> None:
        run_id = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        ts = run_id
        
        stream_path = self.report_path / "stream.ndjson"
        stream_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._write_lock:
            new_events: list[dict[str, Any]] = []
            for result in results:
                event = self._create_file_event(result, run_id, ts)
                new_events.append(event)
            
            existing_lines: dict[str, str] = {}
            if stream_path.exists():
                with stream_path.open("r", encoding="utf-8") as fp:
                    for line in fp:
                        try:
                            existing_event = json.loads(line.strip())
                            path = existing_event.get("path", "")
                            if path:
                                existing_lines[path] = line.strip()
                        except (json.JSONDecodeError, KeyError):
                            continue
            
            for event in new_events:
                path = event["path"]
                new_line = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
                existing_lines[path] = new_line
            
            with stream_path.open("w", encoding="utf-8") as fp:
                for line in existing_lines.values():
                    fp.write(line + '\n')
                fp.flush()
                os.fsync(fp.fileno())
        
        logger.info("Updated %d events in %s (total: %d)", len(new_events), stream_path, len(existing_lines))
    
    def generate_report(self, results: List[ValidationResult]) -> List[dict[str, Any]]:
        run_id = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        ts = run_id
        
        file_events = []
        for result in results:
            event = self._create_file_event(result, run_id, ts)
            file_events.append(event)
        
        return file_events

    def save_report(self, report: List[dict[str, Any]]) -> None:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        dynamic_report_path = self.report_path / f"Report{current_time}.json"
        
        try:
            dynamic_report_path.parent.mkdir(parents=True, exist_ok=True)
            dynamic_report_path.write_text(json.dumps(report, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
            logger.info("Report written to %s", dynamic_report_path)
            
        except PermissionError as e:
            logger.error("Permission denied when writing report to %s: %s", dynamic_report_path, e)
            self._save_report_fallback(report, current_time)
            
        except OSError as e:
            logger.error("OS error when writing report to %s: %s", dynamic_report_path, e)
            self._save_report_fallback(report, current_time)
            
        except Exception as e:
            logger.error("Unexpected error when writing report: %s", e)
            raise

    def _save_report_fallback(self, report: List[dict[str, Any]], current_time: str) -> None:
        fallback_path = Path.cwd() / f"Report{current_time}.json"
        try:
            fallback_path.write_text(json.dumps(report, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
            logger.info("Report written to fallback location: %s", fallback_path)
        except PermissionError as fallback_error:
            logger.error("Permission denied for fallback location %s: %s", fallback_path, fallback_error)
            
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            temp_report_path = temp_dir / f"config-validator-report-{current_time}.json"
            try:
                temp_report_path.write_text(json.dumps(report, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
                logger.info("Report written to temporary location: %s", temp_report_path)
            except Exception as temp_error:
                logger.error("Failed to write report to any location: %s", temp_error)
                raise RuntimeError(f"Unable to write report file. Tried: {fallback_path}, {temp_report_path}")

    def print_summary(self, report: List[dict[str, Any]]) -> None:
        if not report:
            print("No files validated")
            return
        
        valid_count = sum(1 for f in report if f.get("valid", False))
        invalid_count = len(report) - valid_count
        total_errors = sum(f.get("error_count", 0) for f in report)
        
        print(f"\nValidation Summary:")
        print(f"  Valid: {valid_count}")
        print(f"  Invalid: {invalid_count}")
        print(f"  Total errors: {total_errors}")
        print(f"  Files: {len(report)}")

    def run_validation(self) -> List[dict[str, Any]]:
        files = self.discover_files()
        results = self.validate_files(files)
        
        self.stream_to_ndjson(results)
        
        report = self.generate_report(results)
        self.save_report(report)
        self.print_summary(report)
        
        return report

    def validate_specific_files(self, file_paths: List[str]) -> List[dict[str, Any]]:
        files = [Path(p) for p in file_paths]
        results = self.validate_files(files)
        
        self.stream_to_ndjson(results)
        
        report = self.generate_report(results)
        self.save_report(report)
        self.print_summary(report)
        return report

