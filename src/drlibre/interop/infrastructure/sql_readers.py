from django.db import connection

from drlibre.interop.application.ports.inbound import Reader, ReaderKind, Readers
from drlibre.shared_kernel.ids import Id

_READER = """
SELECT u.role = 'ADMIN' AND u.active, p.id
FROM identity_userrecord u
LEFT JOIN organisation_clinicianprofilerecord p ON p.user_id = u.id
WHERE u.id = %s
"""


class SqlReaders(Readers):
    def of(self, user_id: Id | None) -> Reader:
        if user_id is None:
            return Reader.anonymous()
        with connection.cursor() as cursor:
            cursor.execute(_READER, [user_id.value])
            row = cursor.fetchone()
        if row and row[1] is not None:
            return Reader(ReaderKind.CLINICIAN, user_id, Id(row[1]))
        if row and row[0]:
            return Reader(ReaderKind.ADMIN, user_id)
        return Reader(ReaderKind.PATIENT, user_id)
