# Carpooler Bot

Interactive Telegram bot useful to do carpooling.

## Dev guide

### Create new migration

```bash
# in terminal 1
docker compose up db && docker compose down -v --remove-orphans

# in terminal 2
alembic upgrade head
alembic revision --autogenerate -m "Migration name."
```
