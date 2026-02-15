"""Skill-related exceptions."""


class SkillError(Exception):
    """Base exception for all skill-related errors."""


class ParseError(SkillError):
    """Raised when SKILL.md parsing fails."""


class ValidationError(SkillError):
    """Raised when skill properties are invalid."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors if errors is not None else [message]
