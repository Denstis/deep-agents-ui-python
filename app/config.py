"""Configuration management for Deep Agents UI."""

import json
from typing import Optional
from dataclasses import dataclass


@dataclass
class StandaloneConfig:
    """Configuration for standalone deployment."""
    deployment_url: str
    assistant_id: str
    langsmith_api_key: Optional[str] = None


# In-memory storage for configs (in production, use a database)
_configs: dict[str, StandaloneConfig] = {}


def get_config(session_id: str) -> Optional[StandaloneConfig]:
    """Get config for a session."""
    return _configs.get(session_id)


def save_config(session_id: str, config: StandaloneConfig) -> None:
    """Save config for a session."""
    _configs[session_id] = config


def delete_config(session_id: str) -> None:
    """Delete config for a session."""
    if session_id in _configs:
        del _configs[session_id]
