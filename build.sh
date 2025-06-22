#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "->Install requirements"
pip install -r requirements.txt
echo "->Collect static files"
python manage.py collectstatic --noinput
echo "->Make migrations"
python manage.py migrate