from django.db import migrations

FORBID = """
CREATE FUNCTION audit_entries_are_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit entries are append-only: % refused', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$;
CREATE TRIGGER audit_entries_never_changed
    BEFORE UPDATE OR DELETE ON audit_auditentryrecord
    FOR EACH ROW EXECUTE FUNCTION audit_entries_are_append_only();
CREATE TRIGGER audit_entries_never_truncated
    BEFORE TRUNCATE ON audit_auditentryrecord
    FOR EACH STATEMENT EXECUTE FUNCTION audit_entries_are_append_only();
"""

ALLOW = """
DROP TRIGGER audit_entries_never_truncated ON audit_auditentryrecord;
DROP TRIGGER audit_entries_never_changed ON audit_auditentryrecord;
DROP FUNCTION audit_entries_are_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunSQL(FORBID, reverse_sql=ALLOW)]
