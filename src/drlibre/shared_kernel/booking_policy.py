from datetime import timedelta

# A patient books at least this long before the slot starts (spec §5.3).
BOOKING_LEAD_TIME = timedelta(minutes=120)

# A refused booking offers the slots of this many days from the first bookable instant.
ALTERNATIVES_WINDOW = timedelta(days=14)

# Slots are stored, and availabilities searched, this many days ahead.
SLOT_HORIZON_DAYS = 90
