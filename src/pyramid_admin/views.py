# views.py

from functools import partial, wraps
import urllib
import datetime


from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.response import Response, IResponse
from pyramid.decorator import reify
from pyramid.i18n import TranslationStringFactory, get_localizer
from jinja2 import Markup
from webhelpers import util, paginate
from webhelpers.html import HTML



from pyramid_admin.interfaces import IColumnRenderer, ISqlaSessionFactory, IQueryFilter
from pyramid_admin.utils import get_pk_column, get_pk_value


_ = TranslationStringFactory('pyramid_admin')

def action(name=None, **kw):
    """action decorator"""
    def _wrapper(fn):
        kw['name'] = name or fn.__name__
        kw['fn_name'] = fn.__name__
        fn.__action_params__ = kw
        return fn
    return _wrapper


def bulk_action(title, name=None, **kw):
    """bulk action decorator"""
    def _wrapper(fn):
        kw['name'] = name or fn.__name__
        kw['fn_name'] = fn.__name__
        kw['bulk'] = True
        fn.title = title
        fn.__action_params__ = kw
        return fn
    return _wrapper


def column(label):
    """table column decorator"""
    def _wrap(fn):
        @wraps(fn)
        def _wrapper(self, obj):
            res = fn(self, obj)
            return Markup(res)
        _wrapper.__label__ = label
        return _wrapper
    return _wrap


class AdminViewMeta(type):

    def __new__(cls, name, bases, dct):
        ncl = type.__new__(cls, name, bases, dct)
        ncl.__actions__ = {}
        ncl.bulk_actions = []
        for name in dir(ncl):
            val = getattr(ncl, name, None)
            if callable(val) and hasattr(val, '__action_params__'):
                name = val.__action_params__["name"]
                if name in ncl.not_allowed:
                    continue
                val.__action_params__.update(ncl.override.get(name, {}))
                ncl.__actions__[name] = val
                if val.__action_params__.get("bulk"):
                    ncl.bulk_actions.append((name, val.title))
        if ncl.title is None and ncl.model:
            ncl.title = ncl.model.__name__.title()
        return ncl


class AdminViewBase(object):
    """Basic admin class-based view"""
    __metaclass__ = AdminViewMeta

    title = None
    model = None
    form_class = None

    field_list = ['pk', 'repr']
    list_links = ['pk']
    filters = []
    items_per_page = 20
    override = {}

    form_only = None
    form_exclude = None
    form_field_args = None
    form_fields = None
    
    not_allowed = []
    permission = None

    menu_group = ''

    extra_js = []
    extra_css = []

    def __init__(self, site, context, request):
        self.site = site
        self.context = context
        self.request = request
        self.request.view = self
        self.parts = request.matchdict
        self.localizer = get_localizer(request)
        self.list_order = {'field': self.request.GET.get('order'), 'desc': self.request.GET.get('desc')}
        
    def __call__(self):
        action_name = self.parts.get("action", "list")
        if action_name in self.not_allowed:
            raise HTTPNotFound
        action = self.__actions__.get(action_name, None)

        if action is None or not callable(action):
            raise HTTPNotFound

        if "request_method" in action.__action_params__ and \
                self.request.method != action.__action_params__["request_method"]:
            raise HTTPNotFound
        result = action(self)
        registry = self.request.registry
        response = registry.queryAdapterOrSelf(result, IResponse)
        if response is not None:
            return response
        result = self.process_response(result)
        renderer = action.__action_params__['renderer']
        return renderer, result

    def url(self, action=None, obj=None, **q):
        """
        build url for view action or object action (if id param is not None)
        """
        return self.site.url(name=self.__view_name__, action=action, 
            obj_id=self.get_pk_value(obj) if obj else None, **q)

    def page_url(self, page_num):
            url = self.request.path_qs
            return util.update_params(url, pg=page_num)

    def is_allowed(self, action):
        return action not in self.not_allowed

    def message(self, msg, type='success'):
        self.request.session.flash(self.localizer.translate(msg), type)

    def get_pk_value(self, obj):
        """get obj primary key value"""
        raise NotImplementedError

    def get_obj(self):
        """get action context object"""
        raise NotImplementedError

    def get_list_page(self):
        """
        Get objects for list view. 
        Apply filtres and pagination here.
        """
        raise NotImplementedError

    def get_bulk_selected(self, id_list):
        """
        Get objects fo bulk actions.
        """
        raise NotImplementedError

    def get_form(self, obj=None, formdata=None, **kw):
        if self.form_class:
            return self.form_class(formdata, obj, **kw)
        form_class = self._build_form()
        return form_class(formdata, obj, **kw)

    def get_name_label(self, field_name):
        """
        """
        form = self._blank_form
        if ':' in field_name:
            field_name, label = field_name.split(':', 1)
        elif field_name in form:
            label = form[field_name].label.text
        else:
            label = field_name.title().replace('_', ' ')
        return field_name, label

    @action(renderer='pyramid_admin:templates/list.jinja2', index=True)
    def list(self):
        """generic list admin view"""
        return {'page':self.get_list_page()}

    @action(renderer='pyramid_admin:templates/edit.jinja2')
    def update(self):
        """generic edit form admin view"""
        obj = self.get_obj()
        if self.request.method == 'POST':
            form = self.get_form(formdata=self.request.POST, obj=obj)
            if form.validate():
                form.populate_obj(obj)
                self.before_update(obj)
                self._save_obj(obj, False)
                msg = _('Object <strong>"${obj}"</strong> successfully updated.', mapping={'obj':self.repr(obj)})
                self.message(msg)
                next = 'create' if 'another' in self.request.POST else None
                return HTTPFound(self.url(action=next))
        else:
            form = self.get_form(obj)
        return {'obj':obj, 'obj_form': form}

    @action(renderer="pyramid_admin:templates/edit.jinja2")
    def create(self):
        form = self.get_form()
        if self.request.method=="POST":
            form = self.get_form(formdata=self.request.POST)
            if form.validate():
                obj = self.model()
                form.populate_obj(obj)
                self.before_insert(obj)
                self._save_obj(obj, True)
                msg = _('New object <strong>"${obj}"</strong> successfully created.', mapping={'obj':self.repr(obj)})
                self.message(msg)
                next = 'create' if 'another' in self.request.POST else None
                return HTTPFound(self.url(action=next))
        return {'obj':None, 'obj_form': form}

    @action(request_method="POST")
    def delete(self):
        obj = self.get_obj()
        self.before_delete(obj)
        self._delete_obj(obj)
        msg = _('Object <strong>"${obj}"</strong> successfully deleted.', mapping={'obj':self.repr(obj)})
        self.message(msg)
        return HTTPFound(self.url())

    @bulk_action(_("Delete selected"), request_method="POST", renderer="pyramid_admin:templates/confirm_delete.jinja2")
    def bulk_delete(self):
        if not self.is_allowed('delete'):
            raise HTTPNotFound
        ids = self.request.POST.getall('select')
        objects = self.get_bulk_selected(ids)
        if 'confirmed' not in self.request.POST:
            return {'bulk': True, "objects": objects}
        for obj in objects:
            self.before_delete(obj, bulk=True)
            self._delete_obj(obj)
        return HTTPFound(self.url())

    def process_response(self, data):
        return data

    def before_insert(self, obj):
        """pre object creation hook"""
        pass

    def before_update(self, obj):
        """pre object update hook"""
        pass

    def before_delete(self, obj, bulk=False):
        """pre object deletion hook"""
        pass

    def _save_obj(self, obj, created):
        """save object after update or create new one"""
        raise NotImplementedError

    def _delete_obj(self, obj):
        """delete object"""
        raise NotImplementedError

    @reify
    def _blank_form(self):
        """
        Get blank form instance 
        (to get table columns names from form fields labels).
        """
        return self.get_form() 

    @column("#")
    def pk(self, obj):
        """
        value of object primary key
        """
        return self.get_pk_value(obj)

    @column("")
    def repr(self, obj):
        return util.html_escape(unicode(obj))


class Column(object):

    def __init__(self, view, name, label=None):
        self.view = view
        self.label = label or name
        self.name = name

    def title(self):
        field_name = self.name
        url = self.view.request.path_qs
        url = util.update_params(url, order=field_name, desc=None)
        order_ico = ''
        if field_name == self.view.list_order['field'] and not self.view.list_order['desc']:
            order_ico = '<i class="icon-chevron-down"/>'
            url = util.update_params(url, order=field_name, desc=1)
        elif field_name == self.view.list_order['field'] and self.view.list_order['desc']:
            order_ico = '<i class="icon-chevron-up"/>'
            url = util.update_params(url, order=None, desc=None)
        return Markup('<a href="%s">%s</a> %s' % (url, self.label, order_ico))

    def get_val(self, obj):
        raise NotImplementedError

    def _link(self, obj, value):
        return '<a href="%s">%s</a>' % (self.view.url(action="update", obj=obj), value)

    def __call__(self, obj):
        val = self.get_val(obj)
        if self.name in self.view.list_links:
            val = self._link(obj, val)
        return Markup(val)


class MethodColumn(Column):

    def __init__(self, view, name):
        self.view = view
        self.name = name
        self.fn = getattr(self.view, name)
        self.label = self.fn.__label__

    def title(self):
        return self.label

    def get_val(self, obj):
        return self.fn(obj)





