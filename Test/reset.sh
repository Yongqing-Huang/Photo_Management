#!/bin/sh
set -e

echo "Delete temp folder..."
rm -rf temp

echo "Creating temp folder..."
mkdir -p temp/Web temp/Thumb temp/Metadata

echo "Loading database configuration..."

set -a
. ../.env
set +a

echo "Resetting test database..."

mysql \
    -h "$DB_HOST" \
    -P "$DB_PORT" \
    -u "$DB_USER" \
    -p \
    "$DB_NAME" \
    < ../database/reset_db.sql

echo "Done."