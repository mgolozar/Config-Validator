from __future__ import annotations


from abc import ABC, abstractmethod
from typing import List

from ..core.types import ValidationIssue


class ValidationRule(ABC):

    @abstractmethod
    def validate(self, data: dict) -> List[ValidationIssue]:  
        raise NotImplementedError