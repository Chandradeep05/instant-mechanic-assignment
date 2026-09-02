from django.db import migrations

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION validate_booking_vehicle_customer()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM customers_vehicle
        WHERE id = NEW.vehicle_id
          AND customer_id = NEW.customer_id
    ) THEN
        RAISE EXCEPTION 'Booking customer_id must match vehicle owner';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS booking_vehicle_customer_guard ON bookings_booking;

CREATE TRIGGER booking_vehicle_customer_guard
BEFORE INSERT OR UPDATE OF customer_id, vehicle_id
ON bookings_booking
FOR EACH ROW
EXECUTE FUNCTION validate_booking_vehicle_customer();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS booking_vehicle_customer_guard ON bookings_booking;
DROP FUNCTION IF EXISTS validate_booking_vehicle_customer();
"""

def apply_trigger_if_postgres(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(TRIGGER_SQL)

def revert_trigger_if_postgres(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(REVERSE_SQL)

class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0005_remove_booking_version'),
    ]

    operations = [
        migrations.RunPython(apply_trigger_if_postgres, revert_trigger_if_postgres),
    ]
