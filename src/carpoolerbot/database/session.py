from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from carpoolerbot.settings import settings

# Configure engine with connection pool settings to handle stale connections
# Use pre_ping to check connections before using them
# Set pool_recycle to prevent using stale connections
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Additional connections when pool is exhausted
    echo_pool=False,  # Don't log pool checkouts/checkins
)

Session = sessionmaker(engine)
