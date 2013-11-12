from wtforms import Form, validators, TextField, DateTimeField
#from wtforms.ext.dateutil.fields import DateTimeField


class TagForm(Form):
    label = TextField("Label", validators=[validators.Required(), validators.Length(max=20)])
