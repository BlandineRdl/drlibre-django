#!/bin/sh
set -eu
python manage.py migrate --noinput --verbosity 0
python -m scripts.seed
exec gunicorn config.wsgi:application --config docker/gunicorn.conf.py
