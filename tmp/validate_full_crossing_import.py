import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.conf.settings')
import django
django.setup()

from world.areas.the_crossing import ensure_full_canonical_crossing, import_canonical
from world.builder.services import zone_service
from world.area_forge import map_api

rooms = ensure_full_canonical_crossing()
arrival = import_canonical.get_canonical_crossing_arrival_room()
character = type('CharacterProbe', (), {'location': arrival})()
zone_payload = map_api.get_zone_map(character, build_cache=False) if arrival else None
print({
    'room_count': len(rooms),
    'arrival': None if arrival is None else {
        'id': arrival.id,
        'zone': getattr(arrival.db, 'zone', None),
        'zone_id': getattr(arrival.db, 'zone_id', None),
        'builder_id': getattr(arrival.db, 'builder_id', None),
        'build_tags': list(arrival.tags.get(category='build', return_list=True) or []),
    },
    'zone_service_has_the_landing': 'the_landing' in zone_service.list_zones(),
    'zone_service_the_landing_room_count': len(zone_service.list_zones().get('the_landing', {}).get('rooms', {})),
    'zone_map_zone': None if zone_payload is None else zone_payload.get('zone'),
    'zone_map_room_count': None if zone_payload is None else len(zone_payload.get('rooms', [])),
})
