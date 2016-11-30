#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot : SQLAlchemy database definition /u/num8lock
version:    v.0.1
git:   

"""
from sqlalchemy import create_engine, func
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, synonym
from datetime import date, datetime

engine = create_engine('sqlite:///docbot.db', echo=False)
Base = declarative_base()
 
########################################################################
class Library(Base):
    """Main table"""
    __tablename__ = "Library"
 
    id = Column(Integer, primary_key=True)
    version_id  = Column(Integer, nullable=False)
    major = Column(Integer) 
    minor = Column(Integer) 
    micro = Column(Integer)
    topic = Column(String(25))
    module = Column(String(25))
    keytype = Column(String(50))
    keyclass = Column(String(50))
    keyword = Column(String(255))
    url = Column(String)
    header = Column(String)
    body = Column(String)
    footer = Column(String)
    tag = synonym(keytype)

    @property
    def default_version(self):
        _major = str(func.max(self.major))
        _minor = str(func.max(self.minor))
        _micro = str(func.max(self.micro))
        default = ''.join([_major, _minor, _micro])
        return default

    # default_version = synonym(default_version, descriptor=default_version)
    '''
    def __init__(self, version_id, major, minor, 
                micro, topic, module, keytype, 
                keyclass, keyword, url, header, body, 
                footer):
        self.version_id = version_id
        self.major = major
        self.minor = minor
        self.micro = micro
        # TODO: get highest value from major, minor & micro
        self.topic = topic
        self.module = module
        self.keytype = keytype
        self.keyclass = keyclass
        self.keyword = keyword
        self.url = url
        self.header = header
        self.body = body
        self.footer = footer
        # self.default_version = default_version
    '''
########################################################################

########################################################################
class RedditActivity(Base):
    """Main table"""
    __tablename__ = "RedditActivity"
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(10)) 
    username  = Column(String(50), nullable=False) 
    query_keyword  = Column(String)
    query_version = Column(Integer)
    query_topic = Column(String(25))
    query_datetime  = Column(DateTime, default=datetime.utcnow)
    permalink  = Column(String(255))
    replied = Column(String(10))
    replied_datetime = Column(DateTime, default=datetime.utcnow)
 
    def __init__(self, comment_id, username, query_keyword, 
            query_version, query_topic, query_datetime, 
            permalink, replied, replied_datetime):
        self.comment_id = comment_id
        self.username = username
        self.query_keyword = query_keyword
        self.query_version = query_version
        self.query_topic = query_topic
        self.query_datetime = query_datetime
        self.permalink = permalink
        self.replied = replied
        self.replied_datetime = replied_datetime

########################################################################
 
# create tables
Base.metadata.create_all(engine)


