#!/bin/bash
set -e

# Generate .env from Docker environment variables (overrides local .env)
cat > /var/www/html/.env << EOF
APP_NAME=Tarteel
APP_KEY=${APP_KEY}
APP_ENV=${APP_ENV:-local}
APP_DEBUG=${APP_DEBUG:-true}
APP_URL=http://localhost:8000

DB_CONNECTION=pgsql
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_DATABASE=${DB_DATABASE:-tarteel}
DB_USERNAME=${DB_USERNAME:-tarteel}
DB_PASSWORD=${DB_PASSWORD:-tarteel}

REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

QUEUE_CONNECTION=${QUEUE_CONNECTION:-redis}
CACHE_STORE=${CACHE_STORE:-redis}
SESSION_DRIVER=${SESSION_DRIVER:-redis}
BROADCAST_CONNECTION=${BROADCAST_CONNECTION:-reverb}

FASTAPI_URL=${FASTAPI_URL:-http://fastapi:8001}
INTERNAL_API_KEY=${INTERNAL_API_KEY:-dev-internal-key-change-in-production}

REVERB_APP_ID=${REVERB_APP_ID:-tarteel-local}
REVERB_APP_KEY=${REVERB_APP_KEY:-tarteel-local-key}
REVERB_APP_SECRET=${REVERB_APP_SECRET:-tarteel-local-secret}
REVERB_HOST=${REVERB_HOST:-localhost}
REVERB_PORT=${REVERB_PORT:-8080}
REVERB_SCHEME=${REVERB_SCHEME:-http}
EOF

# Discover packages (needs env vars, skipped at build time)
php artisan package:discover --ansi

# Run migrations
php artisan migrate --force

# Start Horizon in background
php artisan horizon &

# Start HTTP server in foreground
exec php artisan serve --host=0.0.0.0 --port=8000
