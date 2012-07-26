from pyramid.config import Configurator
from pyramid_jinja2 import renderer_factory
from blog.models import get_root

from sqlalchemy import create_engine
from wtforms import *

from blog.models import DBSession, metadata, User, Post

from pyramid_admin.views import AdminView
from pyramid_admin.filters import LikeFilter, BoolFilter

def session_factory():
    return DBSession

def allow_all(request):
    return True

class UserForm(Form):
    username = TextField("Login", [validators.Required()])
    name = TextField()
    email = TextField()
    is_active = BooleanField()

class UserAdminView(AdminView):
    model = User
    form_class = UserForm
    field_list = ['id', 'username', 'name', 'email', 'is_active']
    filters = [LikeFilter('username'), LikeFilter('name'), BoolFilter('is_active')]
    __title__ = u"Users ok"


class PostForm(Form):
    user = TextField()
    title = TextField()
    content = TextAreaField()


class PostAdminView(AdminView):
    model = Post
    form_class = PostForm
    field_list = ['id', 'user', 'title']
    __title__ = u"All Posts"


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

    config = Configurator(root_factory=get_root, settings=settings)
    # config.add_translation_dirs('locale/')
    config.include('pyramid_jinja2')
    # config.include('pyramid_tm')

    config.include('pyramid_admin')

    config.add_static_view('static', 'static')
    config.add_view('blog.views.my_view',
                    context='blog.models.MyModel', 
                    renderer="mytemplate.jinja2")

    # config.add_admin_view('user_admin', '/admin/users/', UserAdminView)
    config.add_admin_site('/admin/')
    config.set_sqla_session_factory(session_factory)
    config.set_admin_authz_policy(allow_all)
    config.add_admin_view('users', UserAdminView)
    config.add_admin_view('posts', PostAdminView)
    return config.make_wsgi_app()
