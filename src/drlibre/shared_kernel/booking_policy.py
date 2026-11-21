from datetime import timedelta

# A patient books at least this long before the slot starts (spec §5.3).
BOOKING_LEAD_TIME = timedelta(minutes=120)

# A patient cancels or reschedules at least this long before the start (spec §5.3).
CANCELLATION_WINDOW = timedelta(hours=24)

# A patient is reminded of an appointment starting within this long (spec §5.7).
REMINDER_WINDOW = timedelta(hours=24)

# A patient holds at most this many future online bookings (spec §5.3).
MAX_OPEN_ONLINE = 3

# A refused booking offers the slots of this many days from the first bookable instant.
ALTERNATIVES_WINDOW = timedelta(days=14)

# Slots are stored, and availabilities searched, this many days ahead.
SLOT_HORIZON_DAYS = 90

# A booking verification code stays valid this long.
CODE_LIFETIME = timedelta(minutes=10)

# A sign-in link stays valid this long.
LINK_LIFETIME = timedelta(minutes=15)
