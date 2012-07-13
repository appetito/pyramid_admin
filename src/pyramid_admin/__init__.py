import inspect
from jinja2 import Markup
from zope.interface import Interface

class ISqlaSession(Interface):
    """marker interface for sqla session"""


def add_admin_view(config, name, prefix, view, permission=None):
    actions = []
    obj_actions = []
    view = config.maybe_dotted(view) 
    for nm, attr in inspect.getmembers(view):
        if hasattr(attr, '__action_params__'):
            actions.extend(attr.__action_params__)

        if hasattr(attr, '__obj_action_params__'):
            obj_actions.extend(attr.__obj_action_params__)

    config.add_route(name, prefix)
    config.add_route(name+'_action', prefix+'{action}/')
    config.add_route(name+'_obj_action', prefix+'{id}/{action}/')
    view.__route_name__ = name
    for act in actions:
        a = dict(act)
        if permission:
            a['permission'] = permission
        if a.get('index'):
            a.pop('name')
            a.pop('index')
            config.add_view(route_name=name, view=view, attr=a.pop('fn_name'), **a)
        else:
            config.add_view(route_name=name+'_action', view=view, attr=a.pop('fn_name'), match_param='action=%s' % a.pop('name'), **a)
        
    for act in obj_actions:
        a = dict(act)
        if permission:
            a['permission'] = permission
        config.add_view(route_name=name+'_obj_action', view=view, attr=a.pop('fn_name'), match_param='action=%s' % a.pop('name'), **a)


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


def obj_action(name=None, **kw):
    """object action decorator"""
    def _wrapper(fn):
        kw['name'] = name or fn.__name__
        kw['fn_name'] = fn.__name__
        if hasattr(fn, '__obj_action_params__'):
            fn.__obj_action_params__.append(kw)
        else:
            fn.__obj_action_params__ = [kw]
        return fn
    return _wrapper


def wtf_errors(field):
    ret = ''
    html = u'<ul class="b-field_errors">%s</ul>'
    li = u''.join([u"<li>%s</li>" % e for e in field.errors])
    if li:
        ret = Markup(html % li)
    return ret


def includeme(config):
    config.add_directive('add_admin_view', add_admin_view)
    config.add_static_view(name='_admin_assets', path="pyramid_admin:assets")
    env = config.get_jinja2_environment()
    # import ipdb; ipdb.set_trace()
    env.filters.update({'errors': wtf_errors})
