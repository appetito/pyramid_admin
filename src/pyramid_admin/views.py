# views.py

from functools import partial

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from jinja2 import Markup
from webhelpers import util, paginate

from pyramid_admin import action

class AdminView(object):
    """Basic admin class-based view"""

    field_list = ['id', unicode]
    list_links = ['id']

    def __init__(self, site, context, request):
        self.site = site
        self.context = context
        self.request = request
        # import ipdb; ipdb.set_trace() # XXX BEARKPOINT
        self.parts = request.matchdict
        self.list_order = {'field': self.request.GET.get('order'), 'desc': self.request.GET.get('desc')}

    def get_obj(self):
        obj = self.sess.query(self.model).filter(self.model.id==self.parts['obj_id']).first()
        # import ipdb; ipdb.set_trace() # XXX BEARKPOINT
        if not obj:
            raise HTTPNotFound
        return obj

    def get_list_query(self):
        q = self.sess.query(self.model)
        order = self.list_order['field']
        desc = self.list_order['desc']
        if desc and order:
            order = order + ' desc'
        if order:
            q = q.order_by(order)
        return q

    def apply_filters(self, query):
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

    @action(renderer='pyramid_admin:templates/list.jinja2', index=True)
    def list(self):
        """generic list admin view"""
        query = self.get_list_query()
        query = self.apply_filters(query)
        page_num = self.request.GET.get('pg', 1)
        page = paginate.Page(query, page=page_num, items_per_page=4)
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
                self.sess.add(obj)
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
                self.sess.add(obj)
                raise HTTPFound(self.url())
        return {'obj':None, 'obj_form': form, 'view':self}

    @action(request_method="POST")
    def delete(self):
        obj = self.get_obj()
        self.sess.delete(obj)
        raise HTTPFound(self.url())

    def _build_form(self):
        """ we must introspect model fields and build form"""
        raise NotImplementedError

    def fields(self, obj):
        for f in self.field_list:
            if isinstance(f, basestring):
                val = getattr(obj, f)
                label = f
            elif callable(f):
                val = f(obj)
                label = getattr(f, '__label__', f.__name__)
            if f in self.list_links:
                val = self._wrap_link_field(obj, val)
            yield (f, val)
            
    def _wrap_link_field(self, obj, value):
        return Markup('<a href="%s">%s</a>' % (self.url(action="edit", obj_id=obj.id), value))

    def table_title(self, field_name):
        url = self.url(order=field_name)
        order_ico = ''
        if field_name == self.list_order['field'] and not self.list_order['desc']:
            order_ico = '<i class="icon-chevron-down"/>'
            url = self.url(order=field_name, desc=1)
        elif field_name == self.list_order['field'] and self.list_order['desc']:
            order_ico = '<i class="icon-chevron-up"/>'
        return Markup('<a href="%s">%s</a> %s' % (url, field_name, order_ico))