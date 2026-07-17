from datetime import datetime
from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    id: int
    plan_name: str
    is_active: bool
    starts_at: datetime
    ends_at: datetime

    class Config:
        from_attributes = True
