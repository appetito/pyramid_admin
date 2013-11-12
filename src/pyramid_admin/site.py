# -*- coding: utf-8 -*-
from functools import partial

from zope.interface import Interface

from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden
from pyramid.renderers import render_to_response

from pyramid_admin.interfaces import IAdminView
from pyramid_admin.interfaces import ISqlaSessionFactory
from pyramid_admin.interfaces import IAdminAuthzPolicy


class AdminSite(object):

    permission = 'pyramid_admin:site'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.request.site = self
        self.parts = request.matchdict

    def __call__(self):
        if not self.permitted(self, self.permission):
            raise HTTPForbidden
        model_name = self.parts.get('model_name')
        action = self.parts.get('action', 'list')
        if model_name:
            admin_view = self.request.registry.queryUtility(IAdminView, model_name)
            if admin_view is None:
                raise HTTPNotFound
            if admin_view.permission and not self.permitted(admin_view, admin_view.permission):
                raise HTTPForbidden

            admin_view = admin_view(self, self.context, self.request)
            result = admin_view()
            if isinstance(result, tuple):
                result = render_to_response(*result, request=self.request)
        
            return result

        else:
            return self.index()

    def permitted(self, context, permission):
        """
        authorize admin site usage
        """
        authz_policy = self.request.registry.queryUtility(IAdminAuthzPolicy)
        if authz_policy:
            return authz_policy.permits(self.request, context, permission)
        return False

    def index(self):
        return render_to_response("pyramid_admin/index.jinja2", {}, request=self.request)

    def get_views(self, all=False):
        views = self.request.registry.getUtilitiesFor(IAdminView)
        if not all:
            views = filter(lambda v: self.permitted(v[1], v[1].permission), views)
        return views

    def url(self, name=None, action=None, obj_id=None, **q):
        """
        build url for view action or object action (if obj param is not None)
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

    def menu_iter(self):
        viewlist = self.get_views()
        groups = {}
        for n, v in viewlist:
            if v.menu_group not in groups:
                groups[v.menu_group] = []
            groups[v.menu_group].append((n,v))
        for name, items in groups.items():
            groups[name] = sorted(items, key=lambda g: g[0])
        return sorted(groups.items(), key=lambda g: g[0])


        

