def normalize_iran_mobile(mobile: str) -> str:
    mobile = mobile.strip().replace(" ", "").replace("-", "")

    if mobile.startswith("+98"):
        mobile = "0" + mobile[3:]
    elif mobile.startswith("98"):
        mobile = "0" + mobile[2:]

    if not mobile.startswith("09") or len(mobile) != 11:
        raise ValueError("Invalid Iranian mobile number")

    return mobile
