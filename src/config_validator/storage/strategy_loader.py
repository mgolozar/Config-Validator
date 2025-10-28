import logging
from typing import Any, Dict

from .local_strategy import LocalStrategy

logger = logging.getLogger(__name__)

STRATEGIES = {
    "local": LocalStrategy,
}


def load_storage_strategy(storage_config: Dict[str, Any]):
    if not isinstance(storage_config, dict):
        raise ValueError("storage_config must be a dictionary")
    
    strategy_type = storage_config.get("type")
    if not strategy_type:
        raise ValueError("storage_config must contain 'type' key")
    
    config = storage_config.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("storage_config['config'] must be a dictionary")
    
    strategy_type = strategy_type.lower().strip()
    if strategy_type not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(
            f"Unknown storage strategy: '{strategy_type}'. "
            f"Available strategies: {available}"
        )
    
    strategy_class = STRATEGIES[strategy_type]
    return strategy_class(config)
