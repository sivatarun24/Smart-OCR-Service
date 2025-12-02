#!/bin/sh

echo "Starting Flask server..."
exec gunicorn -b 0.0.0.0:8080 'app:create_app()'