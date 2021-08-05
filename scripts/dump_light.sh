#!/bin/bash

set -ex

pg_dump fragdenstaat_de --schema-only > schema.sql
psql -U postgres -c "DROP DATABASE IF EXISTS fragdenstaat_de_light;"

psql -U postgres -c "CREATE DATABASE fragdenstaat_de_light WITH TEMPLATE fragdenstaat_de OWNER fragdenstaat_de;"
python create_light_sql.py | psql fragdenstaat_de_light
pg_dump fragdenstaat_de_light | gzip -c > fragdenstaat_light.sql.gz
