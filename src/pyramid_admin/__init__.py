import inspect
from jinja2 import Markup
from zope.interface import Interface

from pyramid_admin.site import AdminSite, IAdminView, ISqlaSessionFactory, IAdminAuthzPolicy
from pyramid_admin.views import register_adapters, suggest_view



def wtf_errors(field):
    html = u''.join([u'<span class="help-inline">%s</li>' % e for e in field.errors])
    return Markup(html)


def add_admin_site(config, prefix, view=AdminSite, title="Admin Site", session_factory=None, authz_policy=None):
    config.add_route('admin_root', prefix)
    config.add_route('admin_model', prefix+'{model_name}/')
    config.add_route('admin_model_action', prefix+'{model_name}/{action}/')
    config.add_route('admin_model_obj_action', prefix+'{model_name}/{obj_id}/{action}/')
    view = config.maybe_dotted(view)
    view.title = title
    config.add_view(view, route_name='admin_root')
    config.add_view(view, route_name='admin_model')
    config.add_view(view, route_name='admin_model_action')
    config.add_view(view, route_name='admin_model_obj_action')
    config.add_view(suggest_view, name='_model_suggest', renderer='json')


def add_admin_view(config, name, admin_view):
    admin_view = config.maybe_dotted(admin_view)
    admin_view.__view_name__ = name
    config.registry.registerUtility(admin_view, IAdminView, name)


def set_sqla_session_factory(config, factory):
    factory = config.maybe_dotted(factory)
    config.registry.registerUtility(factory, ISqlaSessionFactory)


def set_admin_authz_policy(config, authz_policy):
    authz_policy = config.maybe_dotted(authz_policy)
    config.registry.registerUtility(authz_policy, IAdminAuthzPolicy)


def includeme(config):
    config.add_directive('set_admin_authz_policy', set_admin_authz_policy)
    config.add_directive('set_sqla_session_factory', set_sqla_session_factory)
    config.add_directive('add_admin_view', add_admin_view)
    config.add_directive('add_admin_site', add_admin_site)
    config.add_static_view(name='_admin_assets', path="pyramid_admin:assets")

    env = config.get_jinja2_environment()
    env.filters.update({'errors': wtf_errors})
    
    register_adapters(config.registry)
