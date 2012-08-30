from pyramid.i18n import TranslationStringFactory
import random

from blog.models import Tag, DBSession

_ = TranslationStringFactory('blog')


def my_view(request):
    tags = DBSession.query(Tag).all()
    return {'project':'blog', 'tags': tags}

def new(request):
    tag = Tag(label="A tagssds %s" % random.random())
    DBSession.add(tag)
    DBSession.commit()
    return {}
