"""Defines dependencies for the agent's run context."""

from dataclasses import dataclass


@dataclass
class Deps:
    """Dependencies needed by the agent's tools."""

    file_path: str
