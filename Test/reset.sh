#!/bin/sh
set -e

echo "Delete temp folder..."
rm -rf temp

echo "Creating temp folder..."
mkdir -p temp/Web temp/Thumb temp/metadata

echo "Resetting test database..."
mysql -u root -p < reset_db.sql

echo "Done."