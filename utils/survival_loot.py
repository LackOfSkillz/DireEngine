from evennia.utils.create import create_object

from typeclasses.objects import Object


def create_harvest_bundle(holder, key, desc, **attributes):
    bundle = create_object(Object, key=key, location=holder)
    bundle.db.desc = desc
    for attr_name, attr_value in attributes.items():
        setattr(bundle.db, attr_name, attr_value)
    if getattr(bundle.db, "weight", None) is None:
        bundle.db.weight = 1.0
    return bundle


def create_simple_item(holder, key, desc, **attributes):
    item = create_object(Object, key=key, location=holder)
    item.db.desc = desc
    for attr_name, attr_value in attributes.items():
        setattr(item.db, attr_name, attr_value)
    if getattr(item.db, "item_value", None) is None:
        item.db.item_value = int(getattr(item.db, "value", 1) or 1)
    if getattr(item.db, "value", None) is None:
        item.db.value = int(getattr(item.db, "item_value", 1) or 1)
    if getattr(item.db, "weight", None) is None:
        item.db.weight = 1.0
    return item