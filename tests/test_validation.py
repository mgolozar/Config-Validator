from __future__ import annotations


from pathlib import Path


from config_validator.core.async_validator import AsyncValidator
from config_validator.core.config import ValidationConfig
from config_validator.storage.local_strategy import LocalStrategy




def test_validate_happy_path(tmp_path: Path) -> None:
    f = tmp_path / "svc.yaml"
    f.write_text(
        """
        service: user-api
        replicas: 3
        image: myregistry.com/user-api:1.4.2
        env:
            DATABASE_URL: postgres://db:5432/x
            REDIS_URL: redis://cache:6379
        """,
        encoding="utf-8",
        )

    # Create test configuration and storage strategy
    config = ValidationConfig()
    storage = LocalStrategy({"base_path": str(tmp_path)})
    validator = AsyncValidator(config, storage)

    res = validator.validate_files_sync([str(f)])[0]
    assert res.valid is True
    assert res.errors == []
    assert res.issues == []
    assert res.registry == "myregistry.com"


 
def test_validate_core_errors(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text(
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

    # Create test configuration and storage strategy
    config = ValidationConfig()
    storage = LocalStrategy({"base_path": str(tmp_path)})
    validator = AsyncValidator(config, storage)

    res = validator.validate_files_sync([str(f)])[0]
     
    assert res.valid is False
    errors = res.errors
    issues = res.issues
    
    # Check that we have validation errors (the exact errors depend on plugin configuration)
    assert len(errors) > 0
    assert len(issues) > 0
    # Backward compatibility: errors should match issue messages
    assert errors == [issue["message"] for issue in issues]
  