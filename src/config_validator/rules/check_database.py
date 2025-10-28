from __future__ import annotations

from typing import Any, List

from ..core.types import ValidationIssue
from ..utils.validation_checks import check_database_name


def validate_database(data: dict, config: Any) -> List[ValidationIssue]:
    """Validate that database name is not forbidden."""
    return check_database_name(data, config)