# Carpooler Bot

Interactive Telegram bot useful to do carpooling.

## Dev guide

### Running tests

```bash
# Install dependencies including pytest
pip install -e '.[dev]'

# Run all tests
PYTHONPATH=src pytest

# Run specific test file
PYTHONPATH=src pytest tests/poll_report/test_message_serializers.py

# Run with coverage
PYTHONPATH=src pytest --cov=carpoolerbot
```

### Create new migration

```bash
# in terminal 1
docker compose up db && docker compose down -v --remove-orphans

# in terminal 2
alembic upgrade head
alembic revision --autogenerate -m "Migration name."
```
