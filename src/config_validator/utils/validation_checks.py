from __future__ import annotations

import re
from typing import Any

from ..core.types import ValidationIssue


def check_required_fields(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that all required fields are present."""
    issues = []
    required = set(config.required_fields)
    missing = sorted(required - set(data.keys()))
    if missing:
        issues.append(ValidationIssue(
            rule_id="schema.required_keys",
            message=f"Missing required keys: {missing}",
            keywords=["schema", "required"]
        ))
    return issues


def check_replicas_range(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that replicas are within the configured range."""
    issues = []
    rep = data.get("replicas")
    if not isinstance(rep, int) or not (config.replicas_min <= rep <= config.replicas_max):
        issues.append(ValidationIssue(
            rule_id="replicas.range",
            message=f"replicas must be an integer between {config.replicas_min} and {config.replicas_max}",
            keywords=["replicas", "range"]
        ))
    return issues


def check_image_format(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that image matches the configured pattern."""
    issues = []
    img = data.get("image")
    if not isinstance(img, str):
        issues.append(ValidationIssue(
            rule_id="image.format",
            message="image must be a string like registry/service:version",
            keywords=["image", "format"]
        ))
    elif not re.compile(config.image_pattern).match(img):
        issues.append(ValidationIssue(
            rule_id="image.format",
            message="image must match <registry>/<service>:<version>",
            keywords=["image", "format"]
        ))
    return issues


def check_env_key_case(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that env variable keys follow the configured case."""
    issues = []
    env = data.get("env")
    if not isinstance(env, dict):
        return issues
    
    if config.env_key_case == "UPPERCASE":
        non_upper = [k for k in env.keys() if not (isinstance(k, str) and k.isupper())]
        if non_upper:
            issues.append(ValidationIssue(
                rule_id="env.key_case",
                message=f"env keys must be UPPERCASE: {sorted(non_upper)}",
                keywords=["env", "case"]
            ))
    elif config.env_key_case == "lowercase":
        non_lower = [k for k in env.keys() if not (isinstance(k, str) and k.islower())]
        if non_lower:
            issues.append(ValidationIssue(
                rule_id="env.key_case",
                message=f"env keys must be lowercase: {sorted(non_lower)}",
                keywords=["env", "case"]
            ))
    return issues


def check_service_name(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that service name is not empty."""
    issues = []
    service_name = data.get("service")
    if not isinstance(service_name, str) or service_name.strip() == "":
        issues.append(ValidationIssue(
            rule_id="service.name_empty",
            message="service name must be a non-empty string",
            keywords=["service", "name", "empty"]
        ))
    return issues


def check_env_values(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that all env values are non-empty strings."""
    issues = []
    env = data.get("env")
    if isinstance(env, dict):
        bad = [k for k, v in env.items() if not isinstance(v, str) or v.strip() == ""]
        if bad:
            issues.append(ValidationIssue(
                rule_id="env.value_empty",
                message=f"env values must be non-empty strings: {sorted(bad)}",
                keywords=["env", "empty"]
            ))
    return issues


def check_database_name(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that database name is not forbidden."""
    issues = []
    env = data.get("env")
    if isinstance(env, dict):
        forbidden = getattr(config, 'forbidden_database_name', 'test')
        bad = [k for k, v in env.items() if k.strip() == "DATABASE_URL" and v.strip() == forbidden]
        if bad:
            issues.append(ValidationIssue(
                rule_id="database.forbidden_name",
                message=f"Database name cannot be '{forbidden}': {sorted(bad)}",
                keywords=["database", "forbidden"]
            ))
    return issues


def check_replicas_1_10(data: dict, config: Any) -> list[ValidationIssue]:
    """Check that replicas are between 1 and 10 (for specific rule)."""
    issues = []
    rep = data.get("replicas")
    if not isinstance(rep, int) or not (1 <= rep <= 10):
        issues.append(ValidationIssue(
            rule_id="replicas.range_1_10",
            message="replicas must be an integer between 1 and 10",
            keywords=["replicas", "range"]
        ))
    return issues

