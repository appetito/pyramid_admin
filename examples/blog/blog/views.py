from pyramid.i18n import TranslationStringFactory

_ = TranslationStringFactory('blog')

def my_view(request):
    return {'project':'blog'}
