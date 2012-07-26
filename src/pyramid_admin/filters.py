# -*- coding: utf-8 -*-

from webhelpers.html import HTML
from jinja2 import Markup

class QueryFilter(object):

    title="Filter"

    def __init__(self, field_name):
        self.field_name = field_name
        self.id = field_name #XXX 

    def apply(self, request, query, model):
        return query

    def update_url(self, url):
        return url

    def display(self, request):
        return ""


class LikeFilter(QueryFilter):

    def __init__(self, field_name, title=None, pattern="%%%s%%"):
        self.field_name = field_name
        self.pattern = pattern
        self.id = field_name #XXX 
        self.term = ""
        self.title = title or "%s like an:" % field_name.title()


    def apply(self, request, query, model):
        if self.term:
            field = getattr(model, self.field_name)
            return query.filter(field.ilike(self.pattern % self.term))
        return query

    def activate(self, request):
        term = request.GET.get(self.id)
        if term:
            self.is_active=True
        self.term = term

    def display(self):
        inp = HTML.tag('input', type="text", name=self.id, value=self.term, class_="filter_input")
        return Markup(inp)


class BoolFilter(QueryFilter):

    def __init__(self, field_name, true="True", false="False", title=None):
        self.field_name = field_name
        self.id = field_name #XXX 
        self.true = true
        self.false = false
        self.title = title or "%s is:" % field_name.title()

    def apply(self, request, query, model):
        if self.is_active:
            field = getattr(model, self.field_name)
            return query.filter(field == self.val)
        return query

    def activate(self, request):
        val = request.GET.get(self.id)
        if val:
            self.is_active=True
        else:
            self.is_active = False
        self.val = val == 't'

    def display(self):
        if self.val:
            inp1 = HTML.tag('input', type="radio", name=self.id, value="f")
            inp2 = HTML.tag('input', type="radio", name=self.id, value="t", checked="checked")
        else:
            inp1 = HTML.tag('input', type="radio", name=self.id, value="f", checked="checked")
            inp2 = HTML.tag('input', type="radio", name=self.id, value="t")
        if not self.is_active:
            inp1 = HTML.tag('input', type="radio", name=self.id, value="f")
            inp2 = HTML.tag('input', type="radio", name=self.id, value="t")
        return Markup('<label class="radio">%s%s</label><label class="radio">%s%s</label>' % (inp1, self.false, inp2, self.true))