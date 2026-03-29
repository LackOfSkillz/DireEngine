from evennia.utils.create import create_object

from typeclasses.objects import Object


def create_harvest_bundle(holder, key, desc, **attributes):
    bundle = create_object(Object, key=key, location=holder)
    bundle.db.desc = desc
    for attr_name, attr_value in attributes.items():
        setattr(bundle.db, attr_name, attr_value)
    return bundle


def create_simple_item(holder, key, desc, **attributes):
    item = create_object(Object, key=key, location=holder)
    item.db.desc = desc
    for attr_name, attr_value in attributes.items():
        setattr(item.db, attr_name, attr_value)
    return item