from wtforms import *

class TagForm(Form):
    label = TextField("Label", validators=[validators.Required(), validators.Length(max=20)])