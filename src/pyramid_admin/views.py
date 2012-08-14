# views.py

from functools import partial, wraps
import urllib
import datetime

from sqlalchemy import orm, or_, types

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.response import Response, IResponse
from pyramid.decorator import reify
from pyramid.i18n import TranslationStringFactory, get_localizer
from jinja2 import Markup
from webhelpers import util, paginate
from webhelpers.html import HTML


from pyramid_admin.forms import model_form
from pyramid_admin.filters import LikeFilter, QuickBoolFilter, QueryFilter
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
        return ncl


class AdminView(object):
    """Basic admin class-based view"""

    __metaclass__ = AdminViewMeta

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
    form_class = None
    menu_group = ''

    def __init__(self, site, context, request):
        self.site = site
        self.context = context
        self.request = request
        self.request.view = self
        self.session = site.session
        self.parts = request.matchdict
        self.localizer = get_localizer(request)
        self.list_order = {'field': self.request.GET.get('order'), 'desc': self.request.GET.get('desc')}
        for i, f in enumerate(self.filters):
            if isinstance(f, basestring) and hasattr(self.model, f):
                typ = get_type(self.model, f)
                filter_class = self.request.registry.queryAdapter(typ, IQueryFilter)
                if not filter_class:
                    continue
                name, label = self.get_name_label(f)
                filter_inst = filter_class(name, label + ':')
                self.filters.pop(i)
                self.filters.insert(i, filter_inst)
            elif isinstance(f, QueryFilter):    
                filter_inst = f
            else:
                raise TypeError("Invalid Filter type ''. \
                    Must by a name of model field or Subclass of pyramid_admin.filters.QueryFilter" % type(f))
            fid = 'f%s' % i
            filter_inst.activate(self.request, fid)

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
        self.process_response(result)
        renderer = action.__action_params__['renderer']
        return renderer, result

    @property
    def title(self):
        return self.model.__name__ + " view" 

    def is_allowed(self, action):
        return action not in self.not_allowed

    def get_obj(self):
        pk_column = get_pk_column(self.model)
        obj = self.session.query(self.model).get(self.parts['obj_id'])
        if not obj:
            raise HTTPNotFound
        return obj

    def get_bulk_selected(self):
        ids = self.request.POST.getall('select')
        objects = self.session.query(self.model).filter(get_pk_column(self.model).in_(ids)).all()
        return objects

    def get_list_query(self):
        q = self.session.query(self.model)
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
                self.before_update(obj)
                self.session.add(obj)
                self.session.flush()
                self.commit()
                msg = _('Object <strong>"${obj}"</strong> successfully updated.', mapping={'obj':self.repr(obj)})
                self.message(msg)
                next = 'new' if 'another' in self.request.POST else None
                return HTTPFound(self.url(action=next))
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
                self.before_insert(obj)
                self.session.add(obj)
                self.session.flush()
                self.commit()
                msg = _('New object <strong>"${obj}"</strong> successfully created.', mapping={'obj':self.repr(obj)})
                self.message(msg)
                next = 'new' if 'another' in self.request.POST else None
                return HTTPFound(self.url(action=next))
        return {'obj':None, 'obj_form': form}

    @action(request_method="POST")
    def delete(self):
        obj = self.get_obj()
        self._delete_obj(obj)
        return HTTPFound(self.url())

    @bulk_action(_("Delete selected"), request_method="POST", renderer="pyramid_admin:templates/confirm_delete.jinja2")
    def bulk_delete(self):
        if not self.is_allowed('delete'):
            raise HTTPNotFound
        objects = self.get_bulk_selected()
        if 'confirmed' not in self.request.POST:
            return {'bulk': True, "objects": objects}
        for obj in objects:
            self._delete_obj(obj)
        return HTTPFound(self.url())

    def _delete_obj(self, obj):
        self.before_delete(obj)
        self.session.delete(obj)
        msg = _('Object <strong>"${obj}"</strong> successfully deleted.', mapping={'obj':self.repr(obj)})
        self.message(msg)
        self.commit()

    def commit(self):
        try:
            self.session.commit()
        except AssertionError: # if pyramid_tm is used
            pass

    def process_response(self, data):
        pass

    def before_insert(self, obj):
        """pre object creation hook"""
        pass

    def before_update(self, obj):
        """pre object update hook"""
        pass

    def before_delete(self, obj):
        """pre object deletion hook"""
        pass

    def _build_form(self):
        """build form for model class"""
        exclude = self.form_exclude or []
        exclude.append(get_pk_column(self.model).name)
        return model_form(self.model,  
                          only=self.form_only, 
                          exclude=exclude, 
                          field_args=self.form_field_args, 
                          fields_override=self.form_fields)

    def message(self, msg, type='success'):
        self.request.session.flash(self.localizer.translate(msg), type)

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
            
    @reify
    def _blank_form(self):
        """
        blank form instance
        """
        return self.get_form()        

    @reify
    def columns(self):
        colls = []
        for f in self.field_list:
            if isinstance(f, basestring):
                name, label = self.get_name_label(f)
                if hasattr(self.model, name):
                    colls.append(Column(self, name, label))
                elif hasattr(self, name):
                    colls.append(MethodColumn(self, name))
        return colls

    @column("#")
    def pk(self, obj):
        """
        value of object primary key
        """
        return get_pk_value(obj)

    @column("")
    def repr(self, obj):
        return unicode(obj)


    
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
        renderer = self.view.request.registry.queryAdapter(get_type(obj, self.name), IColumnRenderer)
        return renderer(getattr(obj, self.name))

    def _link(self, obj, value):
        return '<a href="%s">%s</a>' % (self.view.url(action="edit", obj=obj), value)

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

def like_filter_factory(typ):
    return LikeFilter

def bool_filter_factory(typ):
    return QuickBoolFilter

def register_adapters(reg):
    from sqlalchemy.types import Integer
    from sqlalchemy.types import String
    from sqlalchemy.types import Date
    from sqlalchemy.types import DateTime
    from sqlalchemy.types import Boolean

    reg.registerAdapter(StringRenderer, (Integer,), IColumnRenderer)
    reg.registerAdapter(StringRenderer, (String,), IColumnRenderer)
    reg.registerAdapter(BoolRenderer, (Boolean,), IColumnRenderer)
    reg.registerAdapter(like_filter_factory, (String,), IQueryFilter)
    reg.registerAdapter(bool_filter_factory, (Boolean,), IQueryFilter)


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
    
