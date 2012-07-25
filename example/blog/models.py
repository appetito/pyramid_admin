from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relation
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref
from sqlalchemy.orm import column_property
from sqlalchemy.orm import synonym
from sqlalchemy.orm import joinedload
from sqlalchemy.types import Integer
from sqlalchemy.types import Unicode
from sqlalchemy.types import Boolean
from sqlalchemy.types import UnicodeText
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData


DBSession = scoped_session(sessionmaker())
Base = declarative_base()
metadata = Base.metadata


class User(Base):
    """
    Application's user model.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(Unicode(20), unique=True)
    name = Column(Unicode(50))
    email = Column(Unicode(50))
    is_active = Column(Boolean)

    
class Post(Base):
    """
    Application's user model.
    """
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user = Column(Unicode(20), unique=True)
    title = Column(Unicode(50))
    content = Column(UnicodeText())


class MyModel(object):
    pass

root = MyModel()


def get_root(environ):
    return root
