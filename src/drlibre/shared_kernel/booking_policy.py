from datetime import timedelta

# A patient books at least this long before the slot starts (spec §5.3).
BOOKING_LEAD_TIME = timedelta(minutes=120)

# A refused booking offers the slots of this many days from the first bookable instant.
ALTERNATIVES_WINDOW = timedelta(days=14)

# Slots are stored, and availabilities searched, this many days ahead.
SLOT_HORIZON_DAYS = 90

# A booking verification code stays valid this long.
CODE_LIFETIME = timedelta(minutes=10)

# A sign-in link stays valid this long.
LINK_LIFETIME = timedelta(minutes=15)
