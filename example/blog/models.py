from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
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
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData


DBSession = scoped_session(sessionmaker())
Base = declarative_base()
metadata = Base.metadata

tag_post_table = Table('tag_post_table', metadata,
    Column('tags_id', Integer, ForeignKey('tags.id')),
    Column('posts_id', Integer, ForeignKey('posts.id'))
)


class Tag(Base):
    """
    Tag.
    """
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    label = Column(Unicode(20), unique=True, nullable=False)


class Category(Base):
    """
    Category
    """
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(20), unique=True, nullable=False)

    
class Post(Base):
    """
    Bog post.
    """
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(20), unique=True)
    title = Column(Unicode(50))
    content = Column(UnicodeText())
    category_id = Column(Integer, ForeignKey('categories.id'))

    category = relationship('Category', backref='posts')
    tags = relationship('Tag', backref='posts', secondary=tag_post_table)


class Root(object):
    pass

root = Root()


def get_root(environ):
    return root
