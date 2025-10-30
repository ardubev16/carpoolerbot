import os

# Set environment variables before any imports
os.environ["TELEGRAM_TOKEN"] = "test_token"  # noqa: S105
os.environ["DB_HOST"] = "localhost"
os.environ["DB_NAME"] = "test_db"
os.environ["DB_USERNAME"] = "test_user"
os.environ["DB_PASSWORD"] = "test_password"  # noqa: S105
os.environ["HOLIDAYS_COUNTRY"] = "US"
os.environ["HOLIDAYS_SUBDIV"] = ""
