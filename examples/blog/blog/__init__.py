from pyramid.config import Configurator
from pyramid_jinja2 import renderer_factory
from blog.models import get_root

from sqlalchemy import create_engine
from wtforms import *

from blog.models import DBSession, metadata, User, Post

from pyramid_admin.views import AdminView


class UserForm(Form):
    username = TextField()
    name = TextField()
    email = TextField()

class UserAdminView(AdminView):
    model = User
    form_class = UserForm
    sess = DBSession
    field_list = ['id', 'username', 'name', 'email']
    __title__ = u"Users ok"


class PostForm(Form):
    user = TextField()
    title = TextField()
    content = TextAreaField()


class PostAdminView(AdminView):
    model = Post
    form_class = PostForm
    sess = DBSession
    field_list = ['id', 'user', 'title']
    __title__ = u"All Posts"


def main(global_config, **settings):
    """ This function returns a WSGI application.
    
    It is usually called by the PasteDeploy framework during 
    ``paster serve``.
    """

    engine =  create_engine('sqlite://')
    DBSession.configure(bind=engine)
    metadata.create_all(engine)

    settings = dict(settings)
    settings.setdefault('jinja2.i18n.domain', 'blog')

    config = Configurator(root_factory=get_root, settings=settings)
    config.add_translation_dirs('locale/')
    config.include('pyramid_jinja2')

    config.include('pyramid_admin')

    config.add_static_view('static', 'static')
    config.add_view('blog.views.my_view',
                    context='blog.models.MyModel', 
                    renderer="mytemplate.jinja2")

    # config.add_admin_view('user_admin', '/admin/users/', UserAdminView)
    config.add_admin_site('/admin/')
    config.add_admin_view('users', UserAdminView)
    config.add_admin_view('posts', PostAdminView)
    return config.make_wsgi_app()
