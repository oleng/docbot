#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot : SQLAlchemy database definition /u/num8lock
version:    v.0.1
git:   

"""
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from datetime import date, datetime

engine = create_engine('sqlite:///docbot.db', echo=True)
Base = declarative_base()
 
########################################################################
class Library(Base):
    """Main table"""
    __tablename__ = "Library"
 
    id = Column(Integer, primary_key=True)
    version_id  = Column(Integer, nullable=False)
    version_major  = Column(Integer) 
    version_minor  = Column(Integer) 
    version_micro  = Column(Integer)
    topic  = Column(String(25))
    section  = Column(String(25))
    keyword  = Column(String(25))
    url = Column(String)
    header = Column(String)
    body = Column(String)
    footer = Column(String)
 
    def __init__(self, version_id, version_major, version_minor, version_micro, 
                topic, section, keyword, url, header, body, footer):
        self.version_id = version_id
        self.version_major = version_major
        self.version_minor = version_minor
        self.version_micro = version_micro
        self.topic = topic
        self.section = section
        self.keyword = keyword
        self.url = url
        self.header = header
        self.body = body
        self.footer = footer
########################################################################

########################################################################
class RedditActivity(Base):
    """Main table"""
    __tablename__ = "RedditActivity"
 
    post_id = Column(Integer, primary_key=True) 
    query  = Column(String, nullable=False)
    username  = Column(String(100)) 
    date_time  = Column(DateTime, default=datetime.utcnow)
    permalink  = Column(String(255))
    thread = Column(String(255))
    replied = Column(DateTime, default=datetime.utcnow)
 
    def __init__(self, post_id, query, username, thread_id, 
                topic, section, keyword, url, header, body, footer):
        self.post_id = post_id
        self.query = query
        self.username = username
        self.date_time = date_time
        self.permalink = permalink
        self.thread = thread
        self.replied = replied

########################################################################
 
# create tables
Base.metadata.create_all(engine)


