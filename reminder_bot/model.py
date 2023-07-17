from sqlalchemy import Boolean, Column, Integer, String, Time, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ScheduledReminder(Base):
    __tablename__ = 'scheduled_reminders'

    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer)
    name = Column(String)
    daily = Column(Boolean)
    time = Column(String)
    snooze_until = Column(String)
    completed = Column(Boolean)

# Assuming you have an SQLite database at 'sqlite:///example.db'
engine = create_engine('sqlite:///db.db')

Session = sessionmaker(bind=engine)

# This will create the table in the database if it doesn't exist yet
Base.metadata.create_all(engine)
