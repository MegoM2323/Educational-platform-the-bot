#!/bin/bash
cd /home/mego/Python\ Projects/THE_BOT_platform/backend
export ENVIRONMENT=development
export DEBUG=True
export PYTHONUNBUFFERED=1

# Start server with gunicorn instead of runserver to avoid Daphne issues
python manage.py runserver 0.0.0.0:8000
