from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SubscriptionResponse(BaseModel):
    id: UUID
    plan_name: str
    credits: int
    status: str
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
