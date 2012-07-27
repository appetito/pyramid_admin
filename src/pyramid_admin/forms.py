# -*- coding: utf-8 -*-

from wtforms import Form
from wtforms import Field
from wtforms import PasswordField
from wtforms import TextField
from wtforms import DateField
from wtforms import IntegerField as StupidIntegerField
from wtforms import validators
from wtforms import ValidationError
from wtforms.widgets import TextInput
from wtforms.widgets import HTMLString

from intranet.auth import authenticate


class SuggestInput(TextInput):

    SCRIPT = """
        <script type="text/javascript">
            $(function(){
                $('#%s__ac').autocomplete({
                    'minLength': 2,
                    'delay': 200,
                    source: function(request, response) {
                        %s
                        request['type'] = '%s';
                        $.getJSON("/_model_suggest", request, function(data, status, xhr) {
                            response($.map(data, function(item){
                                return {label: item['%s'],
                                        value: item['%s'],
                                        id: item.id
                                }
                            }))
                        })
                    },
                    select: function(event, ui) {
                        $('#%s').val(ui.item.id);
                    },
                });
            });
        </script>
    """

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('type', 'hidden')
        if 'value' not in kwargs:
             kwargs['value'], val = field._value()
        hidden = '<input %s/>' % self.html_params(name=field.name, **kwargs)
        text = '<input %s/>' % self.html_params(name=field.name + '__ac', id=kwargs['id'] + '__ac', type="text", value=val, class_=kwargs.get('class_'))
        terms = "\n".join(["request['%s'] = request['term'];" % fld for fld in field.search_fields])
        script = self.SCRIPT % (field.name, terms, field.model_class.__name__.lower(), field.ac_label, field.ac_label, field.name)
        return HTMLString(text + hidden + script)


class SuggestField(Field):
    """ autocomplete for models relations"""

    widget = SuggestInput()

    def __init__(self, model_class, display_field, search_fields, ac_label, label='', validators=None, **kwargs):
        super(SuggestField, self).__init__(label, validators, **kwargs)
        self.model_class = model_class
        self.search_fields = search_fields
        self.display_field = display_field
        self.ac_label = ac_label

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0].isdigit():
            self.data = int(valuelist[0])
        else:
            self.data = None

    def _value(self):
        if self.data:
            obj = self.model_class.query.get_by_id(self.data)
            if obj:
                return (self.data, getattr(obj, self.display_field))
        return ('','')