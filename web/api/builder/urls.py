from django.urls import path

from . import views


urlpatterns = [
    path("audit/", views.get_audit_log, name="api-builder-audit"),
    path("zones/", views.list_zones, name="api-builder-zones"),
    path("zones/create/", views.create_zone, name="api-builder-zone-create"),
    path("map/diff/", views.apply_diff, name="api-builder-map-diff"),
    path("map/save-all/", views.save_all, name="api-builder-map-save-all"),
    path("map/export/<str:area_id>/", views.export_map, name="api-builder-map-export"),
    path("map/history/", views.get_diff_history, name="api-builder-map-history"),
    path("map/import/", views.import_map, name="api-builder-map-import"),
    path("map/redo/", views.apply_redo, name="api-builder-map-redo"),
    path("map/undo/", views.apply_undo, name="api-builder-map-undo"),
    path("room/update/<str:room_id>/", views.update_room, name="api-builder-room-update"),
    path("room/assign-npc/", views.assign_room_npc, name="api-builder-room-assign-npc"),
    path("room/remove-npc/", views.remove_room_npc, name="api-builder-room-remove-npc"),
    path("room/assign-item/", views.assign_item_to_room, name="api-builder-room-assign-item"),
    path("room/remove-item/", views.remove_item_from_room, name="api-builder-room-remove-item"),
    path("room/update-item-count/", views.update_room_item_count, name="api-builder-room-update-item-count"),
    path("exit/create/", views.create_exit, name="api-builder-exit-create"),
    path("exit/delete/", views.delete_exit, name="api-builder-exit-delete"),
    path("templates/", views.list_templates, name="api-builder-templates"),
    path("npcs/", views.list_npc_templates, name="api-builder-npcs"),
    path("items/", views.list_item_templates, name="api-builder-items"),
    path("templates/search/", views.search_templates, name="api-builder-templates-search"),
    path("templates/<str:template_id>/", views.get_template, name="api-builder-template-get"),
    path("templates/create/", views.create_template, name="api-builder-template-create"),
    path("templates/<str:template_id>/update/", views.update_template, name="api-builder-template-update"),
    path("move/", views.move_instance, name="api-builder-move"),
    path("delete/", views.delete_instance, name="api-builder-delete"),
    path("spawn/", views.spawn_from_template, name="api-builder-spawn"),
]