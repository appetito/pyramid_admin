from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import scoped_session, sessionmaker, backref
from sqlalchemy.types import Integer, Unicode, UnicodeText, DateTime
from sqlalchemy.ext.declarative import declarative_base


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
    
    def __unicode__(self):
        return "%s" % self.label      


class Category(Base):
    """
    Category
    """
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(20), unique=True, nullable=False)

    def __unicode__(self):
        return "%s" % self.title

    
class Post(Base):
    """
    Blog post.
    """
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(20), unique=True)
    title = Column(Unicode(50))
    content = Column(UnicodeText())
    category_id = Column(Integer, ForeignKey('categories.id'))

    category = relationship('Category', backref='posts')
    tags = relationship('Tag', backref='posts', secondary=tag_post_table)

    def __unicode__(self):
        return "%s" % self.id


class Author(Base):
    """
    Author
    """
    __admindiscover__ = False
    __tablename__ = 'authors'
    id = Column(Integer, primary_key=True)
    login = Column(Unicode(20), unique=True, nullable=False)
    pwd = Column(Unicode(20))

    def __unicode__(self):
        return "%s" % self.login


class Root(object):
    pass

root = Root()


def get_root(environ):
    return root
