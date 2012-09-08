from pyramid.config import Configurator
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid_jinja2 import renderer_factory
from blog.models import get_root

from sqlalchemy import create_engine
from wtforms import *

from blog.models import DBSession, metadata, Post, Tag, Category

from pyramid_admin.sqla import AdminView
from pyramid_admin.filters import LikeFilter, BoolFilter

my_session_factory = UnencryptedCookieSessionFactoryConfig('itsaseekreet')

def session_factory():
    return DBSession

class AdminAuthzPolicy(object):

    def permits(self, request, context, permission):
        return True


class TagAdminView(AdminView):
    model = Tag
    title = 'Tags'

class PostAdminView(AdminView):
    model = Post
    title = 'Posts'

class CategoryAdminView(AdminView):
    model = Category
    title = 'Catagories'
 

def main(global_config, **settings):
    """ This function returns a WSGI application.
    
    It is usually called by the PasteDeploy framework during 
    ``paster serve``.
    """

    engine =  create_engine('sqlite:///blog.db')
    DBSession.configure(bind=engine)
    metadata.create_all(engine)

    settings = dict(settings)
    # settings.setdefault('jinja2.i18n.domain', 'blog')

    config = Configurator(root_factory=get_root, settings=settings, session_factory = my_session_factory)
    # config.add_translation_dirs('locale/')
    config.include('pyramid_jinja2')
    # config.include('pyramid_tm')

    config.include('pyramid_admin')

    config.add_static_view('static', 'static')
    config.add_view('blog.views.my_view',
                    renderer="mytemplate.jinja2")

    config.add_view('blog.views.new', name='new',
                    renderer="json")

    # config.add_admin_view('user_admin', '/admin/users/', UserAdminView)
    config.add_admin_site('/admin/')
    config.set_sqla_session_factory(session_factory)
    config.set_admin_authz_policy(AdminAuthzPolicy())
    config.add_admin_view('tags', TagAdminView)
    config.add_admin_view('categories', CategoryAdminView)
    config.add_admin_view('posts', PostAdminView)
    return config.make_wsgi_app()
