

def get_pk_column(obj):
    """
    Try to get Primary key column of model class or object
    """
    colls = obj.__table__.columns
    for coll in colls:
        if coll.primary_key:
            return coll
    raise TypeError("Can't find model primary key")


def get_pk_value(obj):
    """
    Try to get Primary key value of object
    """
    coll = get_pk_column(obj)
    if coll is not None:
        return getattr(obj, coll.name)