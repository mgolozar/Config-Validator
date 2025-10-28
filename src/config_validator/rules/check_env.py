from __future__ import annotations

from typing import Any, List

from ..core.types import ValidationIssue
from ..utils.validation_checks import check_env_values


def validate_env(data: dict, config: Any) -> List[ValidationIssue]:
    """Ensure all env values are non-empty strings."""
    return check_env_values(data, config)