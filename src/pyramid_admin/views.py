# views.py

from functools import partial

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response, render
from pyramid.response import Response
from jinja2 import Markup
from webhelpers import util, paginate
from webhelpers.html import HTML

from pyramid_admin.interfaces import IColumnRenderer

# def render_iter(values, renderer):
def render_iter(resp):
    yield render(resp.renderer, resp.values)

class DeferResponse(Response):

    def __init__(self, values, renderer, app_iter=None, **kw):
        self.renderer = renderer
        self.values = values
        super(DeferResponse, self).__init__(app_iter=render_iter(self), **kw)
        

def action(name=None, **kw):
    """action decorator"""
    def _wrapper(fn):
        kw['name'] = name or fn.__name__
        kw['fn_name'] = fn.__name__
        fn.__action_params__ = kw
        return fn
    return _wrapper

class AdminViewMeta(type):

    def __new__(cls, name, bases, dct):
        ncl = type.__new__(cls, name, bases, dct)
        ncl.__actions__ = {}
        for name in dir(ncl):
            val = getattr(ncl, name, None)
            if callable(val) and hasattr(val, '__action_params__'):
                ncl.__actions__[val.__action_params__["name"]] = val
        return ncl

class AdminView(object):
    """Basic admin class-based view"""

    __metaclass__ = AdminViewMeta

    field_list = ['id', unicode]
    list_links = ['id']
    filters = []
    items_per_page = 20
    override = []

    def __init__(self, site, context, request):
        self.site = site
        self.context = context
        self.request = request
        self.parts = request.matchdict
        self.list_order = {'field': self.request.GET.get('order'), 'desc': self.request.GET.get('desc')}
        for i, f in enumerate(self.filters):
            f.id = 'f%s' % i
            f.activate(self.request)

    def __call__(self):
        action_name = self.parts.get("action", "list")
        action = self.__actions__.get(action_name, None)
        if action is None or not callable(action):
            raise HTTPNotFound
        result = action(self)
        registry = self.request.registry
        response = registry.queryAdapterOrSelf(result, IResponse)
        if response is None:
            renderer = action.__action_params__['renderer']
            return render_to_response(renderer, result)
        result =  action(self)
        result.update({'request': self.request, 'view': self, 'site': self.site})
        renderer = action.__action_params__['renderer']
        return DeferResponse(renderer, result)

    @property
    def title(self):
        return self.model.__name__ + " view" 


    def get_obj(self):
        obj = self.site.session.query(self.model).filter(self.model.id==self.parts['obj_id']).first()
        if not obj:
            raise HTTPNotFound
        return obj

    def get_list_query(self):
        q = self.site.session.query(self.model)
        order = self.list_order['field']
        desc = self.list_order['desc']
        if desc and order:
            order = order + ' desc'
        if order:
            q = q.order_by(order)
        return q

    def apply_filters(self, query):
        for f in self.filters:
            query = f.apply(self.request, query, self.model)
        return query

    def get_form(self, obj=None, formdata=None):
        if self.form_class:
            return self.form_class(formdata, obj)
        form_class = self._build_form()
        return form_class(formdata, obj)

    def url(self, action=None, obj_id=None, **q):
        """
        build url for view action or object action (if id param is not None)
        """
        return self.site.url(name=self.__view_name__, action=action, obj_id=obj_id, **q)

    def page_url(self, page_num):
            url = self.request.path_qs
            return util.update_params(url, pg=page_num)

    @action(renderer='pyramid_admin:templates/list.jinja2', index=True)
    def list(self):
        """generic list admin view"""
        query = self.get_list_query()
        query = self.apply_filters(query)
        page_num = self.request.GET.get('pg', 1)
        page = paginate.Page(query, page=page_num, items_per_page=self.items_per_page)
        objects = query.all()

        return {'objects': objects, 'page':page, 'view':self}

    @action(renderer='pyramid_admin:templates/edit.jinja2')
    def edit(self):
        """generic edit form admin view"""
        obj = self.get_obj()
        if self.request.method == 'POST':
            form = self.get_form(formdata=self.request.POST, obj=obj)
            if form.validate():
                form.populate_obj(obj)
                self.site.session.add(obj)
                raise HTTPFound(self.url())
        else:
            form = self.get_form(obj)
        return {'obj':obj, 'obj_form': form, 'view':self}

    @action(renderer="pyramid_admin:templates/edit.jinja2")
    def new(self):
        form = self.get_form()
        if self.request.method=="POST":
            form = self.get_form(formdata=self.request.POST)
            if form.validate():
                obj = self.model()
                form.populate_obj(obj)
                self.site.session.add(obj)
                raise HTTPFound(self.url())
        return {'obj':None, 'obj_form': form, 'view':self}

    @action(request_method="POST")
    def delete(self):
        obj = self.get_obj()
        self.site.session.delete(obj)
        raise HTTPFound(self.url())

    def _build_form(self):
        """ we must introspect model fields and build form"""
        raise NotImplementedError

    def fields(self, obj):
        return TableRow(obj, self, self.field_list, self.list_links)
            
    def table_title(self, field_name):
        url = self.request.path_qs
        url = util.update_params(url, order=field_name, desc=None)
        order_ico = ''
        if field_name == self.list_order['field'] and not self.list_order['desc']:
            order_ico = '<i class="icon-chevron-down"/>'
            url = util.update_params(url, order=field_name, desc=1)
        elif field_name == self.list_order['field'] and self.list_order['desc']:
            order_ico = '<i class="icon-chevron-up"/>'
            url = util.update_params(url, order=None, desc=None)
        return Markup('<a href="%s">%s</a> %s' % (url, field_name, order_ico))


class TableRow(object):

    def __init__(self, obj, view, field_list, list_links):
        self.obj = obj
        self.view = view
        self.field_list = field_list
        self.list_links = list_links

    def __iter__(self):
        for f in self.field_list:
            if isinstance(f, basestring):
                renderer = self.view.request.registry.queryAdapter(get_type(self.obj, f), IColumnRenderer)
                val = renderer(getattr(self.obj, f))
                label = f
            elif callable(f):
                val = f(self.obj)
                label = getattr(f, '__label__', f.__name__)
            if f in self.list_links:
                val = self._wrap_link_field(self.obj, val)
            yield (f, val)

    def _wrap_link_field(self, obj, value):
        return Markup('<a href="%s">%s</a>' % (self.view.url(action="edit", obj_id=obj.id), value))


def get_type(obj, fieldname):
    return obj.__table__.columns[fieldname].type


class StringRenderer(object):

    def __init__(self, type):
        self.type = type

    def __call__(self, val, editable=False):
        return val


class BoolRenderer(object):

    def __init__(self, type):
        self.type = type

    def __call__(self, val, editable=False):
        return Markup('<i class="%s"></i>' % ('icon-ok' if val else 'icon-remove'))


def register_adapters(reg):
    from sqlalchemy.types import Integer
    from sqlalchemy.types import String
    from sqlalchemy.types import Date
    from sqlalchemy.types import DateTime
    from sqlalchemy.types import Boolean

    reg.registerAdapter(StringRenderer, (Integer,), IColumnRenderer)
    reg.registerAdapter(StringRenderer, (String,), IColumnRenderer)
    reg.registerAdapter(BoolRenderer, (Boolean,), IColumnRenderer)
    
