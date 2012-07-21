import inspect
from jinja2 import Markup
from zope.interface import Interface

from pyramid_admin.site import AdminSite, IAdminView

class ISqlaSession(Interface):
    """marker interface for sqla session"""




def action(name=None, **kw):
    """action decorator"""
    def _wrapper(fn):
        kw['name'] = name or fn.__name__
        kw['fn_name'] = fn.__name__
        if hasattr(fn, '__action_params__'):
            fn.__action_params__.append(kw)
        else:
            fn.__action_params__ = [kw]
        return fn
    return _wrapper


def wtf_errors(field):
    ret = ''
    html = u'<ul class="b-field_errors">%s</ul>'
    li = u''.join([u"<li>%s</li>" % e for e in field.errors])
    if li:
        ret = Markup(html % li)
    return ret


def add_admin_site(config, prefix, view=AdminSite):
    config.add_route('admin_root', prefix)
    config.add_route('admin_model', prefix+'{model_name}/')
    config.add_route('admin_model_action', prefix+'{model_name}/{action}/')
    config.add_route('admin_model_obj_action', prefix+'{model_name}/{obj_id}/{action}/')
    config.add_view(config.maybe_dotted(view), route_name='admin_root')
    config.add_view(config.maybe_dotted(view), route_name='admin_model')
    config.add_view(config.maybe_dotted(view), route_name='admin_model_action')
    config.add_view(config.maybe_dotted(view), route_name='admin_model_obj_action')

def add_admin_view(config, name, admin_view):
    admin_view = config.maybe_dotted(admin_view)
    admin_view.__view_name__ = name
    config.registry.registerUtility(admin_view, IAdminView, name)

def includeme(config):
    config.add_directive('add_admin_view', add_admin_view)
    config.add_directive('add_admin_site', add_admin_site)
    config.add_directive('add_admin_view', add_admin_view)
    config.add_static_view(name='_admin_assets', path="pyramid_admin:assets")
    env = config.get_jinja2_environment()
    # import ipdb; ipdb.set_trace()

    env.filters.update({'errors': wtf_errors})
