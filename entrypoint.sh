#!/usr/bin/env sh

set -exu

INITIAL_REVISION=9fa0054353e1

# If no upgrade fails assume db is with initial schema without `alembic_version` table.
alembic upgrade head || alembic stamp $INITIAL_REVISION

carpoolerbot
