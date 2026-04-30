#!/bin/bash

# restore a cached database dump for use with pytest-xdist,
# which uses a seperate database with each thread

# this expects a cache-dump.sql file, restored from ci cache

set -e

CPUS=$(nproc --all)
RESTORE="fds_restore"
DB_USER="fragdenstaat_de"

docker compose -f compose-dev.yaml exec db createdb -U $DB_USER -O $DB_USER $RESTORE
docker compose -f compose-dev.yaml exec -T db psql -U $DB_USER -X $RESTORE < cache-dump.sql

for i in $(seq 0 $(($CPUS - 1))); do
    DB_NAME="test_${DB_USER}_gw${i}"
    echo $DB_NAME
    docker compose -f compose-dev.yaml exec db psql -U $DB_USER -c "CREATE DATABASE $DB_NAME WITH TEMPLATE $RESTORE OWNER $DB_USER;"
done
