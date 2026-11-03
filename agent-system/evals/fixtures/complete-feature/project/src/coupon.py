def apply(total: int, percent: int, expired: bool) -> tuple[int, str | None]:
    if expired:
        return total, "COUPON_EXPIRED"
    return total - total * percent // 100, None
