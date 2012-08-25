# -*- coding: utf-8 -*-

from webhelpers.html import HTML
from webhelpers import util
from jinja2 import Markup


class QueryFilter(object):

    def __init__(self, field_name, title=None):
        self.field_name = field_name
        self.title = title or field_name.title()

    def activate(self, request, filter_id):
        self.id = filter_id
        self.value = request.GET.get(self.id)

    def apply(self, request, query, model):
        return query

    def update_url(self, url):
        return url

    def display(self):
        return ""


class LikeFilter(QueryFilter):

    def __init__(self, field_name, title=None, pattern="%%%s%%"):
        super(LikeFilter, self).__init__(field_name, title)
        self.pattern = pattern

    def apply(self, request, query, model):
        if self.value:
            field = getattr(model, self.field_name)
            return query.filter(field.ilike(self.pattern % self.value))
        return query

    def display(self):
        inp = HTML.tag('input', type="text", name=self.id, value=self.value, class_="filter_input")
        return Markup(inp)


class BoolFilter(QueryFilter):

    def __init__(self, field_name, title=None, true="True", false="False"):
        self.field_name = field_name
        self.true = true
        self.false = false
        self.title = title or "%s is:" % field_name.title()

    def apply(self, request, query, model):
        if self.value:
            field = getattr(model, self.field_name)
            return query.filter(field == self.value)
        return query

    def display(self):
        if self.value == 't':
            inp1 = HTML.tag('input', type="radio", name=self.id, value="f")
            inp2 = HTML.tag('input', type="radio", name=self.id, value="t", checked="checked")
        elif self.value == 'f':
            inp1 = HTML.tag('input', type="radio", name=self.id, value="f", checked="checked")
            inp2 = HTML.tag('input', type="radio", name=self.id, value="t")
        else:
            inp1 = HTML.tag('input', type="radio", name=self.id, value="f")
            inp2 = HTML.tag('input', type="radio", name=self.id, value="t")
        return Markup('<label class="radio">%s%s</label><label class="radio">%s%s</label>' % (inp1, self.false, inp2, self.true))


class QuickBoolFilter(BoolFilter):

    def activate(self, request, filter_id):
        super(QuickBoolFilter, self).activate(request, filter_id)
        self.url = request.path_qs

    def display(self):
        true_cls = 'active' if self.value == 't' else ''
        false_cls = 'active' if self.value == 'f' else ''
        true_link = HTML.tag('a', href=util.update_params(self.url, **dict([(self.id,'t')])), c=self.true, class_=true_cls)
        false_link = HTML.tag('a', href=util.update_params(self.url, **dict([(self.id,'f')])), c=self.false, class_=false_cls)
        return Markup(true_link + false_link)