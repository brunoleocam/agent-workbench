import sys

sys.path.insert(0, "src")
import coupon  # noqa: E402

coupon.apply(100, 10, expired=True)
