# -*- coding: utf-8 -*-
from zope.interface import Interface

class IAdminView(Interface):
    """ model admin interface"""

class ISqlaSessionFactory(Interface):
    """ SQLA Session factoru interface"""

class IAdminAuthzPolicy(Interface):
    """ Admin authorization policy"""

class IColumnRenderer(Interface):
    """ Table column renderer """

class IQueryFilter(Interface):
    """ Query filter """