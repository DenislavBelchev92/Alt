#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "->Install requirements"
pip install -r requirements.txt
echo "->Collect static files"
python manage.py collectstatic --noinput


# If migrations fail Refresh the DBs .
# Can happan if tables structure is changed.
# NOTE! Normally should be commented
echo "->Remove tables"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "->Make migrations"
python manage.py migrate    