import uuid


def create_payment_request(amount: int, description: str):
    authority = str(uuid.uuid4())
    payment_url = f"https://example-payment.test/start/{authority}"
    return {
        "authority": authority,
        "payment_url": payment_url,
    }


def verify_payment(authority: str):
    return {
        "success": True,
        "ref_id": "REF-" + authority[:8],
    }
