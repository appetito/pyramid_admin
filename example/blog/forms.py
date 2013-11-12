from wtforms import Form, validators, TextField


class TagForm(Form):
    label = TextField("Label", validators=[validators.Required(), validators.Length(max=20)])
