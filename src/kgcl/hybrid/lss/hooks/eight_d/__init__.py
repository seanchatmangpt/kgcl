"""8D Problem Solving for Knowledge Hooks.

This module implements the 8D (Eight Disciplines) problem solving methodology
specifically for Knowledge Hook failures and quality issues.
"""

from __future__ import annotations

from .steps import Hook8DReport, Hook8DStep, HookProblemTicket

__all__ = ["Hook8DStep", "Hook8DReport", "HookProblemTicket"]
