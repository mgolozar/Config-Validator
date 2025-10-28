from __future__ import annotations

from typing import Any, List

from ..core.types import ValidationIssue
from ..utils.validation_checks import check_replicas_1_10


def validate_replica(data: dict, config: Any) -> List[ValidationIssue]:
    """Ensure all replica values are between 1 and 10."""
    return check_replicas_1_10(data, config)