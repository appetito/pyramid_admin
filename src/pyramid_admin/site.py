# -*- coding: utf-8 -*-
from functools import partial

from zope.interface import Interface

from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden
from pyramid.renderers import render_to_response

from pyramid_admin.interfaces import IAdminView
from pyramid_admin.interfaces import ISqlaSessionFactory
from pyramid_admin.interfaces import IAdminAuthzPolicy


class AdminSite(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.parts = request.matchdict
        self.session = self.request.registry.queryUtility(ISqlaSessionFactory)()

    def __call__(self):
        if not self.authorize():
            raise HTTPForbidden
        model_name = self.parts.get('model_name')
        action = self.parts.get('action', 'list')
        if model_name:
            admin_view = self.request.registry.queryUtility(IAdminView, model_name)
            # import ipdb; ipdb.set_trace()
            if admin_view is None:
                raise HTTPNotFound

            admin_view = admin_view(self, self.context, self.request)
            result = admin_view()
            result.renderer = "pyramid_admin:templates/index.jinja2"
            self.session.commit()
            return result

        else:
            return self.index()

    def authorize(self):
        """
        authorize admin site usage
        """
        authz_policy = self.request.registry.queryUtility(IAdminAuthzPolicy)
        if authz_policy:
            return authz_policy(self.request)
        return False        

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


        

