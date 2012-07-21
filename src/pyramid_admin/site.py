# -*- coding: utf-8 -*-
from functools import partial

from zope.interface import Interface

from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import render_to_response

class IAdminView(Interface):
    """ model admin interface"""



class AdminSite(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.parts = request.matchdict

    def __call__(self):
        model_name = self.parts.get('model_name')
        action = self.parts.get('action', 'list')
        if model_name:
            admin_view = self.request.registry.queryUtility(IAdminView, model_name)
            # import ipdb; ipdb.set_trace()
            if admin_view is None:
                raise HTTPNotFound
            if hasattr(admin_view, action) and callable(getattr(admin_view, action)):
                admin_view = admin_view(self, self.context, self.request)
                act =  getattr(admin_view, action)
                result = act()
                result.update({'request': self.request, 'view': admin_view, 'site': self})
                renderer = act.__action_params__[0]['renderer']
                # import ipdb; ipdb.set_trace()
                return render_to_response(renderer, result)
            else:
                raise HTTPNotFound

        else:
            return self.index()

    # def post_process(self, data):


    def index(self):
        return render_to_response("pyramid_admin:templates/index.jinja2", {'request': self.request, 'site': self})

    def get_views(self):
        return self.request.registry.getUtilitiesFor(IAdminView)


    def url(self, name=None, action=None, obj_id=None, **q):
        """
        build url for view action or object action (if obj_id param is not None)
        """
        if name and action and obj_id:
            fn = partial(self.request.route_path, "admin_model_obj_action", model_name=name, action=action, obj_id=obj_id)
        elif name and action:
            fn = partial(self.request.route_path, "admin_model_action", model_name=name, action=action)
        elif name:
            fn = partial(self.request.route_path, "admin_model", model_name=name)
        else:
            fn = partial(self.request.route_path, 'admin_root')
        if q:
            fn = partial(fn, _query=q)
        return fn()


        

