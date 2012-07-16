# views.py

from functools import partial

from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from pyramid_admin import action, obj_action

class AdminView(object):
    """Basic admin class-based view"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.parts = request.matchdict

    def get_obj(self):
        return self.sess.query(self.model).filter(self.model.id==self.parts['id']).one()

    def get_obj_list(self):
        return self.sess.query(self.model).all()

    def get_form(self, obj=None, formdata=None):
        if self.form_class:
            return self.form_class(formdata, obj)
        form_class = self._build_form()
        return form_class(formdata, obj)

    def url(self, action=None, id=None, **q):
        """
        build url for view action or object action (if id param is not None)
        """
        if action and id:
            fn = partial(self.request.route_path, self.__route_name__ + "_obj_action", action=action, id=id)
        elif action:
            fn = partial(self.request.route_path, self.__route_name__ + "_action", action=action)
        else:
            fn = partial(self.request.route_path, self.__route_name__)
        if q:
            fn = partial(fn, _query=q)
        return fn()

    @action(renderer='pyramid_admin:templates/list.html', index=True)
    def list(self):
        """generic list admin view"""
        objects = self.get_obj_list()
        return {'objects': objects, 'view':self}

    @obj_action(request_method='GET',
                renderer='pyramid_admin:templates/edit.html')
    def edit(self):
        """generic edit form admin view"""
        obj = self.get_obj()
        if not obj:
            raise HTTPNotFound
        form = self.get_form(obj)
        return {'obj':obj, 'obj_form': form, 'view':self}
        
    @obj_action(name='edit',
                request_method='POST',
                renderer='pyramid_admin:templates/edit.html')
    def update(self):
        obj = self.get_obj()
        if not obj:
            raise HTTPNotFound
        form = self.get_form(formdata=self.request.POST, obj=obj)
        if form.validate():
            form.populate_obj(obj)
            self.sess.add(obj)
            return HTTPFound(self.url())
        return {'obj':obj, 'obj_form': form, 'view':self}

    @action(renderer="pyramid_admin:templates/edit.html")
    def new(self):
        form = self.get_form()
        if self.request.method=="POST":
            form = self.get_form(formdata=self.request.POST)
            if form.validate():
                obj = self.model()
                form.populate_obj(obj)
                self.sess.add(obj)
                return HTTPFound(self.url())
        return {'obj':None, 'obj_form': form, 'view':self}

    @obj_action(request_method="POST")
    def delete(self):
        obj = self.get_obj()
        self.sess.delete(obj)
        return HTTPFound(self.url())

    def _build_form(self):
        """ we must introspect model fields and build form"""
        raise NotImplementedError