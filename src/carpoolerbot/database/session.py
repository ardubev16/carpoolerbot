from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from carpoolerbot.settings import settings

engine = create_engine(settings.db_url, pool_pre_ping=True)

Session = sessionmaker(engine)
