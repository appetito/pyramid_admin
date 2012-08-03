# views.py

from functools import partial
import urllib
import datetime

from sqlalchemy import orm, or_, types

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.response import Response, IResponse
from jinja2 import Markup
from webhelpers import util, paginate
from webhelpers.html import HTML

from pyramid_admin.interfaces import IColumnRenderer, ISqlaSessionFactory
from pyramid_admin.utils import get_pk_column, get_pk_value


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
    
    not_allowed = []

    def __init__(self, site, context, request):
        self.site = site
        self.context = context
        self.request = request
        self.request.view = self
        self.parts = request.matchdict
        self.list_order = {'field': self.request.GET.get('order'), 'desc': self.request.GET.get('desc')}
        for i, f in enumerate(self.filters):
            f.id = 'f%s' % i
            f.activate(self.request)

    def __call__(self):
        action_name = self.parts.get("action", "list")
        if action_name in self.not_allowed:
            raise HTTPNotFound
        action = self.__actions__.get(action_name, None)
        if action is None or not callable(action):
            raise HTTPNotFound
        result = action(self)
        registry = self.request.registry
        response = registry.queryAdapterOrSelf(result, IResponse)
        if response is not None:
            return response
        self.process_response(result)
        renderer = action.__action_params__['renderer']
        return renderer, result

    def process_response(self, data):
        pass

    @property
    def title(self):
        return self.model.__name__ + " view" 

    def is_allowed(self, action):
        return action not in self.not_allowed

    def get_obj(self):
        pk_column = get_pk_column(self.model)
        obj = self.site.session.query(self.model).get(self.parts['obj_id'])
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

    def url(self, action=None, obj=None, **q):
        """
        build url for view action or object action (if id param is not None)
        """
        return self.site.url(name=self.__view_name__, action=action, obj=obj, **q)

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
        return {'page':page}

    @action(renderer='pyramid_admin:templates/edit.jinja2')
    def edit(self):
        """generic edit form admin view"""
        obj = self.get_obj()
        if self.request.method == 'POST':
            form = self.get_form(formdata=self.request.POST)
            if form.validate():
                form.populate_obj(obj)
                self.site.session.add(obj)
                self.site.session.flush()
                return HTTPFound(self.url())
        else:
            form = self.get_form(obj)
        return {'obj':obj, 'obj_form': form}

    @action(renderer="pyramid_admin:templates/edit.jinja2")
    def new(self):
        form = self.get_form()
        if self.request.method=="POST":
            form = self.get_form(formdata=self.request.POST)
            if form.validate():
                obj = self.model()
                form.populate_obj(obj)
                self.site.session.add(obj)
                self.site.session.flush()
                return HTTPFound(self.url())
        return {'obj':None, 'obj_form': form}

    @action(request_method="POST")
    def delete(self):
        obj = self.get_obj()
        self.site.session.delete(obj)
        return HTTPFound(self.url())

    @action(request_method="POST", renderer="pyramid_admin:templates/confirm_delete.jinja2")
    def bulk_delete(self):
        if not self.is_allowed('delete'):
            raise HTTPNotFound
        ids = self.request.POST.getall('select')
        objects = self.site.session.query(self.model).filter(get_pk_column(self.model).in_(ids)).all()
        if 'confirmed' not in self.request.POST:
            return {'bulk': True, "objects": objects}
        for obj in objects:
            self.site.session.delete(obj)
        return HTTPFound(self.url())

    def _build_form(self):
        """ we must introspect model fields and build form"""
        raise NotImplementedError

    def pk(self, obj):
        return get_pk_value(obj)

    def fields(self, obj):
        return TableRow(obj, self, self.field_list, self.list_links)
            
    def table_title(self, field_name):
        # import ipdb; ipdb.set_trace()
        if not isinstance(field_name, basestring) or field_name not in self.model.__table__.columns:
            if field_name == unicode:
                return self.title
            return field_name
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
            if isinstance(f, basestring) and hasattr(self.obj, f):
                renderer = self.view.request.registry.queryAdapter(get_type(self.obj, f), IColumnRenderer)
                val = renderer(getattr(self.obj, f))
                label = f
            elif isinstance(f, basestring) and hasattr(self.view, 'column_' + f):
                val = getattr(self.view, 'column_' + f)(self.obj)
                label = f
            elif callable(f):
                val = f(self.obj)
                label = getattr(f, '__label__', f.__name__)
            if f in self.list_links:
                val = self._wrap_link_field(self.obj, val)
            yield (f, val)

    def _wrap_link_field(self, obj, value):
        return Markup('<a href="%s">%s</a>' % (self.view.url(action="edit", obj=obj), value))


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


def to_dict(obj):
    res = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if isinstance(v, (datetime.datetime, datetime.date)):
                v = v.isoformat()
        res[c.name] = v
    return res


def suggest_view(context, request):
    REGISTERED_MODELS = dict(map(lambda t:
                (t[0].class_.dotted_classname.rsplit('.', 1)[-1].lower(), t[0].class_), orm.mapperlib._mapper_registry.items()
            ))
    ret = []

    mtype = request.GET.get('type')
    Model = REGISTERED_MODELS.get(mtype)
    if Model is None:
        return ret
    args = []
    for k, v in request.GET.items():
        if k == 'type' or not v:
            continue
        try:
            if not isinstance(Model.__mapper__.columns.get(k).type,
                    (types.VARCHAR, types.TEXT)):
                continue

            attr = getattr(Model, k)
            val = u'%%%s%%' %(urllib.unquote(v))
            args.append(attr.ilike(val))
        except AttributeError:
            continue

    query = Model.suggest_query() if hasattr(Model, "suggest_query") else None
    if not query:
        session = self.request.registry.queryUtility(ISqlaSessionFactory)()
        query = session.query(Model)
    if args:
        ret = [to_dict(i) for i in query.filter(or_(*args)).limit(10).all()]

    return ret
    
