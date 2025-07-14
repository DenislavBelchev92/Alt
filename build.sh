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
python manage.py flush --no-input
python manage.py migrate --no-input

echo "->Make migrations"
python manage.py migrate