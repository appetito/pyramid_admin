# views.py

import urllib
import datetime

from sqlalchemy import orm, or_, types

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.decorator import reify
from jinja2 import Markup
from webhelpers import util, paginate


# from pyramid_admin.forms import model_form
from wtforms.ext.sqlalchemy.orm import model_form
from pyramid_admin.filters import LikeFilter, QuickBoolFilter, QueryFilter
from pyramid_admin.interfaces import IColumnRenderer, ISqlaSessionFactory, IQueryFilter
from pyramid_admin.utils import get_pk_column, get_pk_value
from pyramid_admin.views import AdminViewBase, MethodColumn, Column
from pyramid_admin.filters import LikeFilter, QuickBoolFilter, QueryFilter

class AdminView(AdminViewBase):
    """Basic admin class-based view for sqla models"""

    def __init__(self, site, context, request):
        super(AdminView, self).__init__(site, context, request)
        self.session = self.request.registry.queryUtility(ISqlaSessionFactory)()

    def get_obj(self):
        pk_column = get_pk_column(self.model)
        obj = self.session.query(self.model).get(self.parts['obj_id'])
        if not obj:
            raise HTTPNotFound
        return obj

    def get_bulk_selected(self, id_list):
        objects = self.session.query(self.model).filter(get_pk_column(self.model).in_(id_list)).all()
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

    def get_list_page(self):
        query = self.get_list_query()
        query = self.apply_filters(query)
        page_num = self.request.GET.get('pg', 1)
        page = paginate.Page(query, page=page_num, items_per_page=self.items_per_page)
        return page

    def apply_filters(self, query):
        for f in self.filters:
            query = f.apply(self.request, query, self.model)
        return query

    def _save_obj(self, obj, created):
        if not orm.util.has_identity(obj):
            self.session.add(obj)
        self.commit()

    def _delete_obj(self, obj):
        self.session.delete(obj)
        self.commit()

    def commit(self):
        try:
            self.session.commit()
        except AssertionError: # if pyramid_tm is used
            pass

    def _build_form(self):
        """build form for model class"""
        exclude = self.form_exclude or []
        exclude.append(get_pk_column(self.model).name)
        return model_form(self.model,  
                          db_session=self.session,
                          only=self.form_only, 
                          exclude=exclude, 
                          field_args=self.form_field_args)

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
                    colls.append(SQLAColumn(self, name, label))
                elif hasattr(self, name):
                    colls.append(MethodColumn(self, name))
        return colls

    def get_pk_value(self, obj):
        return get_pk_value(obj)



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


class SQLAColumn(Column):

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