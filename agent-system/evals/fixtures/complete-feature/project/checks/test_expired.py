import sys

sys.path.insert(0, "src")
import coupon  # noqa: E402

assert coupon.apply(100, 10, expired=True) == (100, "COUPON_EXPIRED")
