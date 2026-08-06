"""Compatibility exports for the former provider-specific module name."""

from app.services.ai.gpt_service import _clean_and_parse_json, generate_exam

__all__ = ["_clean_and_parse_json", "generate_exam"]
