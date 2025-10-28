from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationIssue:
    rule_id: str
    message: str
    keywords: List[str] = field(default_factory=list)
    search_keys: List[str] = field(default_factory=list)
