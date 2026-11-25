"""The one SQL wording of a bookable stored slot, `s` in `scheduling_slot`, shared by every read."""

# A slot an open hold covers, plus the type's buffer, is taken; an expired hold frees it.
NOT_HELD = """
NOT EXISTS (
    SELECT 1 FROM booking_bookingholdrecord bh
    WHERE bh.clinician_id = s.clinician_id AND bh.expires_at > %(now)s
      AND s.start < bh."end" + make_interval(mins => {buffer}) AND s."end" > bh.start
)
"""

# Like placement, a type with a room needs one active room of its department free all along.
# The range overlap form lets PostgreSQL use the `appointment_room_period` index.
ROOM_FREE = """
(NOT {kind}.needs_room OR EXISTS (
    SELECT 1 FROM organisation_roomrecord r
    WHERE r.department_id = {department} AND r.active
      AND NOT EXISTS (
          SELECT 1 FROM booking_appointmentrecord a
          WHERE a.room_id = r.id AND a.status NOT IN ('CANCELLED', 'NO_SHOW')
            AND tstzrange(a.start, a."end", '[)') && tstzrange(s.start, s."end", '[)')
      )
))
"""
