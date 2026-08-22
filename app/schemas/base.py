from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DictComparableModel(BaseModel):
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            return self.model_dump() == other
        return super().__eq__(other)
