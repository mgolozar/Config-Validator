from __future__ import annotations
import importlib
import pkgutil
from typing import Any, Callable, List

_DEF_PKG = "config_validator.rules"
ValidatorFn = Callable[[dict, Any], List]


def load_rules(config=None) -> List[ValidatorFn]:
    """Load all validator functions from the rules package."""
    validators: List[ValidatorFn] = []
    pkg = importlib.import_module(_DEF_PKG)
    
    for m in pkgutil.iter_modules(pkg.__path__, prefix=f"{_DEF_PKG}."):
        try:
            module = importlib.import_module(m.name)
            for attr_name in dir(module):
                if not attr_name.startswith('_'):
                    attr = getattr(module, attr_name)
                    # Find all functions that start with 'validate_'
                    if callable(attr) and attr_name.startswith('validate_'):
                        validators.append(attr)
        except Exception:
            continue
    
    return validators