from pydantic import BaseModel


class PaymentCreateRequest(BaseModel):
    amount: int
    description: str = "Teacher Assistant Subscription"


class PaymentCreateResponse(BaseModel):
    payment_url: str
    authority: str


class PaymentVerifyResponse(BaseModel):
    success: bool
    ref_id: str | None = None
    message: str
