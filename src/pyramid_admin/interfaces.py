# -*- coding: utf-8 -*-
from zope.interface import Interface

class IAdminView(Interface):
    """ model admin interface"""

class ISqlaSessionFactory(Interface):
    """ SQLA Session factoru interface"""

class IAdminAuthzPolicy(Interface):
    """ Admin authorization policy"""

    def permits(request, context, permission):
        """
        Provided a permission (a string or unicode object), a context  and a request object. 
        Return True if the permission is granted in this context to the user implied by the request. 
        Return False if this permission is not granted in this context to this user
        """

class IColumnRenderer(Interface):
    """ Table column renderer """

class IQueryFilter(Interface):
    """ Query filter """