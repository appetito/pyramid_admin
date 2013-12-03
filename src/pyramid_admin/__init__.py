import inspect
from jinja2 import Markup
from zope.interface import Interface
from pyramid.i18n import get_localizer, TranslationStringFactory
from pyramid.threadlocal import get_current_request

from pyramid_admin.site import AdminSite, IAdminView, ISqlaSessionFactory, IAdminAuthzPolicy
# from pyramid_admin.sqla import register_adapters



def wtf_errors(field):
    html = u''.join([u'<span class="help-inline">%s</span>' % e for e in field.errors])
    return Markup(html)


def add_admin_site(config, prefix, view=AdminSite, title="Admin Site",
     session_factory=None, authz_policy=None, permission='pyramid_admin:site'):
    config.add_route('admin_root', prefix)
    config.add_route('admin_model', prefix+'{model_name}/')
    config.add_route('admin_model_action', prefix+'{model_name}/{action}/')
    config.add_route('admin_model_obj_action', prefix+'{model_name}/{obj_id}/{action}/')
    view = config.maybe_dotted(view)
    view.title = title
    view.permission = permission
    config.add_view(view, route_name='admin_root')
    config.add_view(view, route_name='admin_model')
    config.add_view(view, route_name='admin_model_action')
    config.add_view(view, route_name='admin_model_obj_action')
    # config.add_view(suggest_view, name='_model_suggest', renderer='json')


def add_admin_view(config, name, admin_view, permission=None):
    admin_view = config.maybe_dotted(admin_view)
    admin_view.__view_name__ = name
    admin_view.permission = permission
    config.registry.registerUtility(admin_view, IAdminView, name)


def add_admin_include(config, admins, admin_view=None, menu_group=None,
        permission='pyramid_admin:site'):
    """ Include module's admin """
    def all_subclasses(cls):
        """
        Find all subclasses of a given class
        """
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                for g in all_subclasses(s)]

    def convert(name):
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    if not admin_view:
        admin_view = 'pyramid_admin.sqla:AdminView'
    admin_view = config.maybe_dotted(admin_view)
    if isinstance(admins, basestring):
        admins = [admins]
    for adm in admins:
        mdl = None
        models = []
        try:
            config.include('%s.admin' % adm) # Ex: blog.admin
        except ImportError:
            pass
            #module = __import__(adm)
        module = config.maybe_dotted(adm)
        for val in ['model', 'models']:
            if hasattr(module, val):
                mdl = getattr(module, val)
                break
        if not mdl:
            continue
        try:
            models = all_subclasses(vars(mdl)['Base'])
        except KeyError: pass
        try:
            models.extend(all_subclasses(vars(mdl)['DeclarativeBase']))
        except KeyError: pass
        # unique list of models
        models = list(set(models))
        for model in models:
            if not getattr(model, '__admindiscover__', True):
                # If the value of '__adminidiscover__' is set to False, the
                # administration's interface for model won't be generated
                continue
            if model in [reg.model for x, reg in \
                    config.registry.getUtilitiesFor(IAdminView)]:
                # Already regitered
                continue
            # Ex: tag
            # Auto generation of classes
            # The following code =>
            # >>> class TagAdminView(AdminView):
            # >>>     model = Tag
            # >>>     menu_group = 'blog'
            # becomes =>
            params = {'model': model}
            if menu_group:
                params['menu_group'] = menu_group
            view = type('%sAdminView' % model.__name__, (admin_view,),
                    params)
            # url: blog_tag
            config.add_admin_view('%s_%s' % (
                module.__name__.lower(), convert(model.__name__)),
                view,
                permission=permission
            )


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
    config.add_directive('add_admin_include', add_admin_include)
    config.add_static_view(name='_admin_assets', path="pyramid_admin:assets")

    config.add_jinja2_extension('jinja2.ext.i18n')
    config.add_translation_dirs('pyramid_admin:locale')

    env = config.get_jinja2_environment()
    env.filters.update({'errors': wtf_errors})
    env.install_gettext_callables(gettext, ngettext)
    # register_adapters(config.registry)
    config.add_jinja2_search_path('pyramid_admin:templates')

tsf = TranslationStringFactory('pyramid_admin')

def gettext(msg):
    req = get_current_request()
    localizer = get_localizer(req)
    ts = tsf(msg)
    return localizer.translate(ts)

def ngettext(singular, plural, n):
    req = get_current_request()
    localizer = get_localizer(req)
    return localizer.pluralize(singular, plural, n, domain='pyramid_admin')
