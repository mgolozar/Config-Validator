from __future__ import annotations

from typing import Any, List

from ..core.types import ValidationIssue
from ..utils.validation_checks import (
    check_required_fields,
    check_replicas_range,
    check_image_format,
    check_env_key_case,
    check_service_name,
)


def validate_core(data: dict, config: Any) -> List[ValidationIssue]:
    """Run core validation checks."""
    issues = []
    issues.extend(check_required_fields(data, config))
    issues.extend(check_replicas_range(data, config))
    issues.extend(check_image_format(data, config))
    issues.extend(check_env_key_case(data, config))
    issues.extend(check_service_name(data, config))
    return issues
