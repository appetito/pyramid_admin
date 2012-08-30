# -*- coding: utf-8 -*-

from wtforms import Form
from wtforms import Field
from wtforms import PasswordField
from wtforms import TextField
from wtforms import DateField
from wtforms import IntegerField as StupidIntegerField
from wtforms import validators
from wtforms import ValidationError
from wtforms.ext.sqlalchemy.orm import model_fields
from wtforms.widgets import TextInput
from wtforms.widgets import HTMLString


class SuggestInput(TextInput):

    SCRIPT = """
        <script type="text/javascript">
            $(function(){
                $('#%(name)s__ac').autocomplete({
                    'minLength': 2,
                    'delay': 200,
                    source: function(request, response) {
                        %(terms)s
                        request['type'] = '%(type)s';
                        $.getJSON("/suggest/", request, function(data, status, xhr) {
                            response($.map(data, function(item){
                                return {label: item['%(ac_label)s'],
                                        value: item['%(ac_label)s'],
                                        id: item.id
                                }
                            }))
                        })
                    },
                    select: function(event, ui) {
                        $('#%(name)s').val(ui.item.id);
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
        text = '<input %s/>' % self.html_params(name=field.name + '__ac', id=kwargs['id'] + '__ac', 
            type="text", value=val, class_=kwargs.get('class_'))
        terms = "\n".join(["request['%s'] = request['term'];" % fld for fld in field.search_fields])
        script = self.SCRIPT % {
                                    'name': field.name, 
                                    'terms': terms, 
                                    'type': field.model_class.__name__.lower(), 
                                    'ac_label': field.ac_label
                                }
        return HTMLString(text + hidden + script)


class SuggestField(Field):
    """ autocomplete for models relations"""

    widget = SuggestInput()

    def __init__(self, label, model_class, display_field, search_fields, ac_label, validators=None, **kwargs):
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


# def model_form(model, base_class=Form, only=None, exclude=None, field_args=None, converter=None, fields_override=None):
#     """
#     Create a wtforms Form for a given SQLAlchemy model class::

#         from wtforms.ext.sqlalchemy.orm import model_form
#         from myapp.models import User
#         UserForm = model_form(User)

#     :param model:
#         A SQLAlchemy mapped model class.
#     :param base_class:
#         Base form class to extend from. Must be a ``wtforms.Form`` subclass.
#     :param only:
#         An optional iterable with the property names that should be included in
#         the form. Only these properties will have fields.
#     :param exclude:
#         An optional iterable with the property names that should be excluded
#         from the form. All other properties will have fields.
#     :param field_args:
#         An optional dictionary of field names mapping to keyword arguments used
#         to construct each field object.
#     :param converter:
#         A converter to generate the fields based on the model properties. If
#         not set, ``ModelConverter`` is used.
#     """
#     field_dict = model_fields(model, only, exclude, field_args, converter)
#     if fields_override:
#         field_dict.update(fields_override)
#     return type(model.__name__ + 'Form', (base_class, ), field_dict)


def model_form(model, db_session=None, base_class=Form, only=None,
    exclude=None, field_args=None, converter=None, exclude_pk=True,
    exclude_fk=True, type_name=None, fields_override=None):
    """
    Create a wtforms Form for a given SQLAlchemy model class::

        from wtalchemy.orm import model_form
        from myapp.models import User
        UserForm = model_form(User)

    :param model:
        A SQLAlchemy mapped model class.
    :param db_session:
        An optional SQLAlchemy Session.
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments used
        to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    :param exclude_pk:
        An optional boolean to force primary key exclusion.
    :param exclude_fk:
        An optional boolean to force foreign keys exclusion.
    :param type_name:
        An optional string to set returned type name.
    """
    class ModelForm(base_class):
        """Sets object as form attribute."""
        def __init__(self, *args, **kwargs):
            if 'obj' in kwargs:
                self._obj = kwargs['obj']
            super(ModelForm, self).__init__(*args, **kwargs)

    if not exclude:
        exclude = []
    model_mapper = model.__mapper__
    for prop in model_mapper.iterate_properties:
        if not hasattr(prop, 'direction') and prop.columns[0].primary_key:
            if exclude_pk:
                exclude.append(prop.key)
        if hasattr(prop, 'direction') and  exclude_fk and \
                prop.direction.name != 'MANYTOMANY':
            for pair in prop.local_remote_pairs:
                exclude.append(pair[0].key)
    type_name = type_name or str(model.__name__ + 'Form')
    field_dict = model_fields(model, db_session, only, exclude, field_args,
        converter)
    if fields_override:
        field_dict.update(fields_override)
    return type(type_name, (ModelForm, ), field_dict)