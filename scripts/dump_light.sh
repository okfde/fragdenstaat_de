#!/bin/bash

set -ex

pg_dump fragdenstaat_de --schema-only > schema.sql
dropdb --if-existsfragdenstaat_de_light
createdb --template=fragdenstaat_de --owner=fragdenstaat_de fragdenstaat_de_light

python create_light_sql.py | psql fragdenstaat_de_light
pg_dump fragdenstaat_de_light | gzip -c > fragdenstaat_light.sql.gz
