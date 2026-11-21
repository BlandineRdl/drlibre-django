from datetime import timedelta

# A patient books at least this long before the slot starts (spec §5.3).
BOOKING_LEAD_TIME = timedelta(minutes=120)
