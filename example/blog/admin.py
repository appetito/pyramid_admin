"""
Admin views
"""
import datetime

from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from pyramid_admin.sqla import AdminView
from pyramid_admin.views import bulk_action

from blog.models import Post, Tag, Category
from blog.forms import TagForm


def includeme(config):
    config.add_admin_view('tags', TagAdminView)
    config.add_admin_view('categories', CategoryAdminView)
    config.add_admin_view('posts', PostAdminView)


class TagAdminView(AdminView):
    model = Tag
    title = 'Tags'
    menu_group = 'blog'
    form_class = TagForm
#    field_list = ['id', 'label']


class PostAdminView(AdminView):
    model = Post
    title = 'Posts'
    menu_group = 'blog'
    #not_allowed = ['set_date']

    # An example of an action
    @bulk_action("Set the date", request_method="POST")
    def bulk_set_date(self):
        """ Duplicate a post """
        if not self.is_allowed('set_date'):
            raise HTTNotFound
        ids = self.request.POST.getall('select')
        objects = self.get_bulk_selected(ids)
        for obj in objects:
            obj.date = datetime.datetime.now()
            self._save_obj(obj, False)
        if objects:
            self.message('Object(s) updated')
        return HTTPFound(self.url())


class CategoryAdminView(AdminView):
    model = Category
    title = 'Categories'
    menu_group = 'blog'
