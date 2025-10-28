from __future__ import annotations

import json
from pathlib import Path

import pytest

from config_validator.core.async_validator import AsyncValidator
from config_validator.core.config import ValidationConfig
from config_validator.storage.local_strategy import LocalStrategy


def test_yaml_validation_and_report_generation(tmp_path: Path) -> None:
    """Test complete flow: validate YAML file, generate report, and verify JSON content."""
    # Create test YAML file
    test_yaml = tmp_path / "test-service.yaml"
    test_yaml.write_text(
        """
service: user-api
replicas: 3
image: myregistry.com/user-api:1.4.2
env:
    DATABASE_URL: postgres://db:5432/database
    REDIS_URL: redis://cache:6379
        """,
        encoding="utf-8",
    )
    
    # Create validation config and storage strategy
    config = ValidationConfig(replicas_min=1, replicas_max=10)
    storage = LocalStrategy({"base_path": str(tmp_path)})
    validator = AsyncValidator(config, storage)
    
    # Validate the file
    results = validator.validate_files_sync([str(test_yaml)])
    
    # Verify validation result
    assert len(results) == 1
    result = results[0]
    assert result.path == str(test_yaml)
    assert result.valid is True, f"Expected valid but got errors: {result.errors}"
    assert result.errors == []
    assert result.issues == []
    assert result.registry == "myregistry.com"
    assert result.data is not None
    assert result.data["service"] == "user-api"
    assert result.data["replicas"] == 3
    
    # Generate report manually
    report_data = {
        "path": result.path,
        "valid": result.valid,
        "errors": result.errors,
        "registry": result.registry,
        "data": result.data
    }
    
    # Save report to JSON file
    report_file = tmp_path / "validation_report.json"
    with report_file.open("w", encoding="utf-8") as f:
        json.dump({"summary": {"valid": result.valid, "errors": len(result.errors)}}, f)
    
    # Verify report file exists
    assert report_file.exists()
    
    # Read and verify JSON content
    with report_file.open("r", encoding="utf-8") as f:
        report_json = json.load(f)
    
    assert "summary" in report_json
    assert report_json["summary"]["valid"] is True
    assert report_json["summary"]["errors"] == 0


def test_yaml_validation_with_errors_and_report(tmp_path: Path) -> None:
    """Test validation of invalid YAML and verify error reporting in JSON."""
    
    # Create invalid YAML file (empty DATABASE_URL)
    test_yaml = tmp_path / "invalid-service.yaml"
    test_yaml.write_text(
        """
service: user-api
replicas: 2
image: myregistry.com/user-api:1.0.0
env:
    DATABASE_URL: ""
    REDIS_URL: redis://cache:6379
        """,
        encoding="utf-8",
    )
    
    # Create validation config and storage strategy
    config = ValidationConfig(replicas_min=1, replicas_max=10)
    storage = LocalStrategy({"base_path": str(tmp_path)})
    validator = AsyncValidator(config, storage)
    
    # Validate the file
    results = validator.validate_files_sync([str(test_yaml)])
    
    # Verify validation result has errors
    assert len(results) == 1
    result = results[0]
    assert result.path == str(test_yaml)
    assert result.valid is False
    assert len(result.errors) > 0
    assert len(result.issues) > 0
    
    # Generate and save report
    report_file = tmp_path / "error_report.json"
    report_data = {
        "path": result.path,
        "valid": result.valid,
        "errors": result.errors,
        "registry": result.registry,
    }
    
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, separators=(",", ":"), ensure_ascii=False)

    
    # Verify error report
    assert report_file.exists()
    with report_file.open("r", encoding="utf-8") as f:
        report_json = json.load(f)
    
    assert report_json["valid"] is False
    assert len(report_json["errors"]) > 0
    # Check that empty env value error is present
    assert any("env" in error.lower() or "empty" in error.lower() 
               for error in report_json["errors"])


def test_multiple_yaml_files_and_aggregated_report(tmp_path: Path) -> None:
    """Test validation of multiple YAML files and generate aggregated report."""
    
    # Create multiple test files
    files_data = [
        ("valid1.yaml", """
service: api-1
replicas: 5
image: registry.com/api-1:v1.0
env:
    KEY1: value1
"""),
        ("valid2.yaml", """
service: api-2
replicas: 3
image: registry.com/api-2:v2.0
env:
    KEY2: value2
"""),
        ("invalid1.yaml", """
service: api-3
replicas: 2
image: registry.com/api-3:v3.0
env:
    KEY3: ""
"""),
    ]
    
    test_files = []
    for filename, content in files_data:
        test_file = tmp_path / filename
        test_file.write_text(content, encoding="utf-8")
        test_files.append(test_file)
    
    # Validate all files
    config = ValidationConfig(replicas_min=1, replicas_max=10)
    storage = LocalStrategy({"base_path": str(tmp_path)})
    validator = AsyncValidator(config, storage)
    
    file_paths = [str(f) for f in test_files]
    results = validator.validate_files_sync(file_paths)
    
    # Verify results
    assert len(results) == 3
    
    # Count valid/invalid
    valid_count = sum(1 for r in results if r.valid)
    invalid_count = sum(1 for r in results if not r.valid)
    
    assert valid_count == 2
    assert invalid_count == 1
    
    # Generate aggregated report
    report_data = {
        "summary": {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "total_files": len(results)
        },
        "files": [
            {
                "path": r.path,
                "valid": r.valid,
                "errors": r.errors,
                "registry": r.registry
            }
            for r in results
        ]
    }
    
    # Save report
    report_file = tmp_path / "aggregated_report.json"
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, separators=(",", ":"), ensure_ascii=False)

    
    # Verify aggregated report
    assert report_file.exists()
    with report_file.open("r", encoding="utf-8") as f:
        report_json = json.load(f)
    
    assert report_json["summary"]["valid_count"] == 2
    assert report_json["summary"]["invalid_count"] == 1
    assert report_json["summary"]["total_files"] == 3
    assert len(report_json["files"]) == 3
    
    # Verify individual file results
    valid_files = [f for f in report_json["files"] if f["valid"]]
    invalid_files = [f for f in report_json["files"] if not f["valid"]]
    
    assert len(valid_files) == 2
    assert len(invalid_files) == 1
    
    # Verify invalid file has errors
    invalid_file = invalid_files[0]
    assert len(invalid_file["errors"]) > 0
    assert "invalid1.yaml" in invalid_file["path"]

