from collections import deque
from pathlib import Path

from evennia import create_object
from evennia.utils.search import search_tag
from world.area_forge.ai.adjudicator import adjudicate_area_spec
from world.area_forge.extract.ocr import extract_ocr_bundle, is_exit_command
from world.area_forge.model.confidence import classify_confidence, score_label_confidence
from world.area_forge.paths import area_namespace, artifact_paths
from world.area_forge.review import generate_review_flags, save_review_report
from world.area_forge.serializer import save_area_spec

try:
    from PIL import Image
except ImportError:  # pragma: no cover - runtime dependency guard
    Image = None


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"

MAP_PATH = Path(__file__).resolve().parent.parent / "maps" / "CrossingMap (1).png"
BUILD_DIR = Path(__file__).resolve().parent.parent / "build"
USE_OCR = True
USE_AI_ADJUDICATION = True

DIR_ALIASES = {
    "north": ["n"],
    "south": ["s"],
    "east": ["e"],
    "west": ["w"],
    "northeast": ["ne"],
    "northwest": ["nw"],
    "southeast": ["se"],
    "southwest": ["sw"],
}

OPPOSITE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
}

BLUE_WATER = (0, 0, 255)
SPECIAL_EXIT_NAME_CANDIDATES = [
    "gate",
    "arch",
    "bridge",
    "stair",
    "path",
    "walk",
    "ramp",
    "pier",
    "ferry",
    "dock",
    "entry",
    "veranda",
    "yard",
]

MARKER_PALETTES = {
    "gray": {
        (153, 128, 153),
        (102, 128, 102),
        (204, 170, 204),
        (204, 213, 204),
        (153, 170, 153),
        (102, 128, 153),
        (153, 128, 102),
        (204, 170, 153),
        (204, 213, 153),
        (153, 213, 153),
    },
    "red": {(255, 0, 0)},
    "green": {(0, 255, 0)},
    "yellow": {(255, 255, 0)},
    "cyan": {(0, 255, 255)},
    "magenta": {(255, 0, 255)},
}

STREET_STEMS = [
    "Ashwalker",
    "Bellfound",
    "Blackbar",
    "Briar Crown",
    "Candlekeep",
    "Crowstep",
    "Dunspire",
    "Gallowmere",
    "Harrowgate",
    "Ironvein",
    "Kingshade",
    "Lanternrest",
    "Marrowmarket",
    "Mournbrick",
    "Oakshield",
    "Rookward",
    "Saltward",
    "Sablemarch",
    "Stonewake",
    "Thornwall",
    "Wardenhall",
    "Weathercrown",
    "Wyrmwatch",
    "Yewmarket",
]

LANE_STEMS = [
    "Amberwick",
    "Baker's",
    "Brasshook",
    "Cedarcoil",
    "Charter",
    "Copperveil",
    "Driftmint",
    "Elmbrook",
    "Fletcher's",
    "Glassmere",
    "Guilder's",
    "Hearthline",
    "Juniper",
    "Larkspur",
    "Mallow",
    "Needlethread",
    "Pennybright",
    "Quillwater",
    "Riverlamp",
    "Rosecart",
    "Silverspun",
    "Tallowmarket",
    "Willowbend",
    "Wrenfeather",
]

ALLEY_STEMS = [
    "Blackcup",
    "Brinehook",
    "Caskshadow",
    "Catspaw",
    "Cinder",
    "Cracked Bell",
    "Dockrat",
    "Dregs",
    "Gutterlight",
    "Hookrope",
    "Knucklebone",
    "Lanternhook",
    "Mossstep",
    "Nightbarrel",
    "Ratwhistle",
    "Rook's",
    "Sootlace",
    "Tanner's Cut",
    "Wharfmire",
    "Whispergut",
    "Winker's",
    "Wyrmash",
]

DISTRICT_SCENES = {
    "north": [
        "Ashlar-fronted town houses and disciplined guild walls keep the road feeling orderly despite the traffic.",
        "Stone lintels, iron lamps, and careful mortar lines speak of old money and civic pride.",
        "Well-swept stoops, shuttered upper windows, and the occasional painted crest lend this stretch a deliberate dignity.",
    ],
    "market": [
        "Uneven cobbles are polished smooth by carts, boots, and the constant shuffle of trade.",
        "Timber-fronted shops lean over the street on carved brackets, their upper stories almost close enough to shake hands across.",
        "Canvas awnings, hanging signs, and open stallfronts make the air feel busy even before voices reach you.",
    ],
    "civic": [
        "Broader paving stones and heavier stonework give the district a public, official weight.",
        "Masons' work shows in squared corners, carved coping, and stout public facades built to last centuries.",
        "Notice boards, iron rails, and disciplined foot traffic make this quarter feel watched and maintained.",
    ],
    "south": [
        "The cobbles here are older and more patched, with muddy seams and wagon-rutted joints between the stones.",
        "Stone ground floors support timber upper stories that jut out above the lane in a tangle of beams and shutters.",
        "Wash lines, side doors, and hard-used thresholds give the quarter a lived-in roughness rather than polish.",
    ],
    "river": [
        "River damp clings to the stone, carrying tar, fish, rope, and silt through every passing breeze.",
        "Warehouse walls, dock stores, and weathered timbers make the street feel built for labor before beauty.",
        "The nearer the water lies, the more the masonry gives way to patched planks, mooring posts, and salt-stained wood.",
    ],
}

DISTRICT_SURFACES = {
    "north": [
        "The cobbles are tight-set and well cared for, with only the thinnest seams of dirt caught between them.",
        "Pale stone pavers sit straighter here than elsewhere in the city, as though some magistrate once measured each course by hand.",
        "The roadway shows money in its upkeep: trimmed edges, swept gutters, and repair work done before cracks become wounds.",
    ],
    "market": [
        "The street underfoot is scuffed by stalls, drays, and the thousand small trades that wear a city smooth.",
        "Cobbles dip and rise where generations of cart traffic have worried the road into shallow grooves.",
        "Rainwater has polished the high stones bright while the low places keep grit, peelings, and market dust.",
    ],
    "civic": [
        "The paving is broader and more formal here, cut to look respectable even when mud and bootmarks try to say otherwise.",
        "Square stone courses give the quarter a deliberate order, as if the city expects its business conducted upright and in public.",
        "The road holds itself in measured lines, with gutters chiseled clean and corners faced in heavier stone.",
    ],
    "south": [
        "The stones here have been patched more than once, old cobbles giving way to newer pieces wherever the road has sunk.",
        "Mud, straw, and soot collect in the joins between the stones, and the whole stretch looks walked harder than it is cleaned.",
        "The roadway has a tired look to it, its older paving burdened by cheap repairs and constant use.",
    ],
    "river": [
        "Moisture beads on the stone and leaves the lower courses slick where the river wind keeps everything faintly damp.",
        "Salt bloom, silt, and tracked-in dock grime dull the paving to a riverfront sheen.",
        "The street takes on the wear of nearby wharves, with damp boards, patched stone, and rope marks all but worked into the ground.",
    ],
}

DISTRICT_BUILDINGS = {
    "north": [
        "Stone-fronted houses stand shoulder to shoulder with carved lintels, leaded panes, and expensive roofs pitched to shed the weather neatly.",
        "Narrow but elegant facades crowd the road with plaster, dressed stone, and the occasional iron crest bracketed above a doorway.",
        "Guild walls and private residences trade turns along the block, all of them built with more confidence than haste.",
    ],
    "market": [
        "Shops of timber and plaster lean over the way on old braces, their upper stories pushing close above the passing traffic.",
        "Storefronts crowd together in a patchwork of stone ground floors, painted timber fronts, and hanging boards that creak in the wind.",
        "Awning poles, jutting signs, and cramped upper rooms make the whole lane feel built by merchants seizing every spare foot of frontage.",
    ],
    "civic": [
        "Public buildings and respectable halls keep their fronts broader here, with heavier doors, squared steps, and less patience for clutter.",
        "Official stonework dominates the quarter, broken now and then by practical wood annexes and covered entries built for clerks and petitioners.",
        "The buildings look commissioned rather than improvised, each facade trying in its own way to project permanence.",
    ],
    "south": [
        "Timber upper stories jut over stone lower floors, throwing long strips of shade across side doors, stoops, and shuttered windows.",
        "Low businesses, boarding rooms, and narrow homes press together here in a haphazard run of beams, plaster, and smoke-darkened wood.",
        "The block is built in practical layers: stone where strength matters, timber where cost matters more.",
    ],
    "river": [
        "Warehouses, lofts, chandlers, and rougher riverside houses stand in weathered rows of stone, plank, and tarred timber.",
        "The architecture grows more workmanlike near the water, with hoists, sheds, reinforced doors, and patched walls replacing grace.",
        "River trade has written itself into the buildings here through crane arms, loading doors, storage lofts, and warped timber galleries.",
    ],
}

DISTRICT_SOUNDS = {
    "north": [
        "Conversation carries in lower tones here, interrupted by carriage wheels, distant bells, and the clipped pace of people who know where they are going.",
        "The district sounds restrained: polished boots, muted cart axles, and the occasional barked instruction behind a respectable gate.",
        "You hear less shouting than elsewhere in the city, and more the discreet noises of servants, shopmen, and passing officials.",
    ],
    "market": [
        "The air is full of barter, hawking, laughter, wheel-rattle, and the endless clink of a city making money.",
        "Voices overlap from every direction, with traders calling, laborers cursing, and someone always arguing over price or quality.",
        "The lane keeps up a constant market noise of boots, drays, open shutters, and talk spilling from every active doorway.",
    ],
    "civic": [
        "The quarter carries a public hush beneath its traffic, broken by posted proclamations read aloud, official errands, and measured footsteps.",
        "Sound moves differently here, echoing from broader walls and public fronts with a discipline the market never manages.",
        "You hear the regular cadence of orderly business: scribes, guards, messengers, and petitioners all feeding the same civic machinery.",
    ],
    "south": [
        "This part of the city sounds rougher and more private, full of half-heard talk from doorways, kitchen clatter, and cart wheels complaining at every rut.",
        "The street carries house-noise as much as trade-noise here: children somewhere out of sight, a slammed shutter, a muttered bargain at a side entrance.",
        "Between the louder moments you catch the ordinary sounds of dense living: wash buckets, cheap music, coughs behind shutters, and dogs stirring in yards.",
    ],
    "river": [
        "Rope strain, dock calls, gull noise, and the slap of water against pilings never quite let the riverfront fall quiet.",
        "Even inland from the wharves, the sound of river labor reaches this far in creaking timbers, shouted counts, and the knock of wood on wood.",
        "The river announces itself in boatwork, cranes, hoists, and the restless noise of freight being shifted somewhere nearby.",
    ],
}

DISTRICT_SMELLS = {
    "north": [
        "The air smells of lamp oil, clean mortar, wet stone, and the faint perfume of better-kept houses.",
        "You catch polished wood, cold iron, and the ghost of expensive kitchens behind closed shutters.",
        "The scents here are clean by city measure: rain on stone, banked hearths, horses kept at a remove, and trimmed greenery from private courts.",
    ],
    "market": [
        "Bread steam, spice dust, fresh straw, animal sweat, and old cabbage all share the same moving air.",
        "The smells change by the doorway here: yeast, onions, leather, lamp smoke, bruised fruit, and whatever is roasting two stalls over.",
        "Everything the city buys or eats seems to leave some trace in the air, from fish brine to sweet cakes to vinegar and dye.",
    ],
    "civic": [
        "Dusty paper, damp wool, lamp smoke, and old stone give the quarter its sober civic smell.",
        "The air carries less food and more work: wax, ink, rainwater, oiled hinges, and the stale breath of public chambers.",
        "Here the scent is one of masonry, wet cloaks, and the bureaucratic life of a city run from desks and halls.",
    ],
    "south": [
        "Cookfire smoke, spilled ale, wash water, and long-settled soot cling to the quarter.",
        "The street smells of packed living: broth, horse dung, damp wood, cheap tobacco, and yesterday's ash.",
        "Tarred shutters, crowded kitchens, and overworked hearths lend the block a warm but worn smell.",
    ],
    "river": [
        "Tar, fish, wet rope, brine, and river mud are impossible to mistake.",
        "The wind off the water brings silt, pitch, damp timber, and the raw metallic tang of working docks.",
        "Everything near the river smells a little saltier, a little older, and a good deal more hard-used.",
    ],
}

INTERSECTION_OPENINGS = [
    "{street} crosses {lane} here, the meeting laid out in worn cobbles polished by generations of boots, hooves, and cartwheels.",
    "At the junction of {street} and {lane}, the city opens just enough for traffic to sort itself before pressing onward again.",
    "{street} meets {lane} at a busy knot of paving stones where wheel ruts, bootmarks, and old repairs all overlap.",
    "The crossing of {street} and {lane} feels like a true city hinge, where one stream of life cuts cleanly across another.",
]

STREET_OPENINGS = [
    "This stretch of {street} runs straight and sure through The Landing, its stones set for steady traffic and long sightlines.",
    "{street} keeps a deliberate north-south line here, carrying the eye along walls, lamps, and the measured rhythm of the block.",
    "The road lengthens into a clear run of {street}, a proper street built for through-traffic rather than loitering.",
    "Here {street} feels broad by city standards, the sort of road meant to move carts, riders, and purpose without apology.",
]

LANE_OPENINGS = [
    "{lane} threads east and west through the district, a lived-in lane of shopfronts, side doors, and close-built eaves.",
    "This part of {lane} slips between crowded facades, intimate enough for voices to carry from one doorstep to the next.",
    "{lane} runs laterally through the block here, narrower and more personal than the great streets but no less busy for it.",
    "There is a practiced, everyday rhythm to {lane}, where trade, gossip, and small errands seem to share the same cobbles.",
]

STREET_ALLEY_OPENINGS = [
    "{street} narrows at the mouth of {alley}, where the broader road sheds a little of its dignity into shadow and side traffic.",
    "The line of {street} breaks slightly where {alley} cuts away, inviting shortcuts, deliveries, and less public business.",
    "{alley} feeds into {street} here through a tighter gap between buildings, turning the main road briefly more secretive.",
]

LANE_ALLEY_OPENINGS = [
    "{lane} brushes past {alley} here, where the lane pinches tight between workaday walls and back-door thresholds.",
    "The mouth of {alley} opens onto {lane} in a cramped seam of stone, shadow, and habitual side traffic.",
    "{lane} is interrupted here by {alley}, a narrower cut that feels more like neighborhood knowledge than public route.",
]

ALLEY_OPENINGS = [
    "{alley} slips through a tighter seam of the city, more intimate than grand and easy to miss if you are not looking for it.",
    "This part of {alley} feels like it belongs to residents, porters, and anyone else with reason to favor the back way.",
    "The alley narrows the city down to stone, timber, and shadow, all packed close enough to turn a whisper private.",
]

POSITION_DETAILS = {
    "North Reach": [
        "The block still carries something of the road's cleaner beginning here.",
        "You stand toward the upper end of this run, where the district has not yet loosened into its rougher habits.",
    ],
    "Upper Stretch": [
        "This part of the road feels settled into itself, neither gateway nor terminus but a lived middle ground.",
        "The upper stretch keeps a steady pace of movement, as though most traffic here already knows its business.",
    ],
    "Midway": [
        "This is the kind of middle block where a city's real character tends to show itself.",
        "At mid-run, the street feels most itself, stripped of gateway flourish and dead-end privacy alike.",
    ],
    "Lower Stretch": [
        "The road has begun to pick up a different character here, shaped by whatever quarter lies further down.",
        "Something in the block suggests transition, as if the street is leaning toward another district's habits.",
    ],
    "South Reach": [
        "This far along, the run feels closer to its next district than to the one behind you.",
        "The lower reach carries the sense of a street preparing to hand you off to another part of the city.",
    ],
    "West Reach": [
        "The western end of the lane has a slight edge-of-block feel, with traffic gathering and then peeling away.",
        "This reach feels closer to a boundary, where the lane begins or ends its own small story.",
    ],
    "Western Run": [
        "The lane is settled but still alert here, close enough to one end that arrivals and departures shape the mood.",
        "This western run feels worked-in and familiar, with enough passing trade to keep every doorway attentive.",
    ],
    "Eastern Run": [
        "The road is carrying you toward another knot of city life from here, and the buildings seem to know it.",
        "This eastern run feels a little more hurried, as if people are usually going somewhere just beyond sight.",
    ],
    "East Reach": [
        "The far reach of the lane feels like a hand extended toward the next block over.",
        "Here the run seems to narrow toward whatever waits beyond the next turn or frontage.",
    ],
    "Outer Bend": [
        "The alley still feels open enough here to be claimed by foot traffic rather than secrecy.",
    ],
    "Crook": [
        "The bend in the way gives the passage a slyer feel, with sightlines shortening and sound carrying oddly.",
    ],
    "Kink": [
        "The cramped middle of the cut collects the small signs of hard use: scuffs on stone, soot on plaster, and handprints near corners.",
    ],
    "Turn": [
        "The alley changes its mind a little at this point, and the architecture closes in around that hesitation.",
    ],
    "Inner Bend": [
        "This innermost part of the alley feels most hidden from the main roads, claimed by those who use it often.",
    ],
}

MARKER_SCENES = {
    "gray": "This stretch feels ordinary by city standards, shaped more by daily use than by any one institution.",
    "red": "Painted shutters, brighter signage, and better-kept frontages suggest a notable business or house close at hand.",
    "green": "Well-used doorways, posted notices, and steady purposeful traffic hint at a guildhall, service house, or respected trade nearby.",
    "yellow": "The street opens a little wider here, as if the city expects people to pause, gather, or choose their way forward.",
    "cyan": "Boundary stones, walls, or the edge of a distinct enclave make this stretch feel nearer the city's margin than its heart.",
    "magenta": "Something about this spot marks it as a special hinge in the city, a place where routes and intentions converge.",
}

REGION_RULES = [
    (lambda x, y: y < 205 and x < 320, "Cleric's Residential Cloister", "north"),
    (lambda x, y: y < 220 and x >= 320, "North Crossing", "north"),
    (lambda x, y: x < 110 and y < 440, "West Gate Approach", "north"),
    (lambda x, y: x > 735 and y < 420, "Northeast Gate Approach", "north"),
    (lambda x, y: x < 120 and 640 <= y <= 760, "Prison Quarter", "south"),
    (lambda x, y: x < 220 and y > 860, "South Docks", "river"),
    (lambda x, y: x > 640 and y > 715, "Riverpine Circle", "river"),
    (lambda x, y: y > 720, "Riverfront", "river"),
    (lambda x, y: y < 430, "Upper Crossing", "market"),
    (lambda x, y: y < 670, "Central Crossing", "civic"),
    (lambda x, y: True, "Lower Crossing", "south"),
]


def _get_tagged(tag, category):
    matches = list(search_tag(tag, category=category))
    return matches[0] if matches else None


def _cleanup_existing_area(valid_node_ids, valid_exit_ids, namespace):
    tagged_objects = list(search_tag(namespace["area_tag"][0], category=namespace["area_tag"][1]))
    tagged_objects.sort(key=lambda obj: 0 if getattr(obj, "db_destination", None) else 1)
    for obj in tagged_objects:
        if getattr(obj, "destination", None) is not None:
            exit_tags = set(obj.tags.get(category=namespace["exit_category"], return_list=True) or [])
            if not exit_tags or exit_tags.isdisjoint(valid_exit_ids):
                obj.delete()
            continue

        node_tags = set(obj.tags.get(category=namespace["node_category"], return_list=True) or [])
        if not node_tags or node_tags.isdisjoint(valid_node_ids):
            obj.delete()


def _load_map_image(map_path=None):
    map_path = Path(map_path) if map_path else MAP_PATH
    if Image is None:
        raise RuntimeError("The Landing builder requires Pillow to parse the Crossing map image.")
    if not map_path.exists():
        raise FileNotFoundError(f"The Landing map image was not found: {map_path}")
    return Image.open(map_path).convert("RGB")


def _detect_components(img, palette):
    pixels = img.load()
    width, height = img.size
    visited = [[False] * width for _ in range(height)]
    components = []

    for y in range(height):
        for x in range(width):
            if visited[y][x] or pixels[x, y] not in palette:
                continue
            queue = deque([(x, y)])
            visited[y][x] = True
            points = []
            while queue:
                cur_x, cur_y = queue.popleft()
                points.append((cur_x, cur_y))
                for next_x, next_y in (
                    (cur_x + 1, cur_y),
                    (cur_x - 1, cur_y),
                    (cur_x, cur_y + 1),
                    (cur_x, cur_y - 1),
                ):
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and not visited[next_y][next_x]
                        and pixels[next_x, next_y] in palette
                    ):
                        visited[next_y][next_x] = True
                        queue.append((next_x, next_y))

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            if 10 <= box_width <= 13 and 10 <= box_height <= 13:
                components.append({
                    "x": int(round((min_x + max_x) / 2)),
                    "y": int(round((min_y + max_y) / 2)),
                })

    return components


def _detect_nodes(img, area_slug="landing"):
    nodes = []
    for kind, palette in MARKER_PALETTES.items():
        for component in _detect_components(img, palette):
            nodes.append({"kind": kind, **component})

    merged = []
    for node in sorted(nodes, key=lambda item: (item["y"], item["x"])):
        duplicate = None
        for existing in merged:
            if abs(node["x"] - existing["x"]) <= 3 and abs(node["y"] - existing["y"]) <= 3:
                duplicate = existing
                break
        if duplicate is None:
            merged.append(node)

    for node in merged:
        node["id"] = f"{area_slug}_{node['x']}_{node['y']}"

    return merged


def attach_ocr_labels_to_nodes(nodes, ocr_lines, max_distance=80):
    for node in nodes:
        best_line = None
        best_distance = None

        for line in ocr_lines:
            dx = node["x"] - line["x"]
            dy = node["y"] - line["y"]
            distance = (dx * dx + dy * dy) ** 0.5

            if distance <= max_distance and (best_distance is None or distance < best_distance):
                best_line = line
                best_distance = distance

        node["ocr_label"] = best_line["text"] if best_line else None
        node["ocr_label_confidence"] = best_line["confidence"] if best_line else 0.0
        node["ocr_label_quality"] = best_line.get("quality_score", 0.0) if best_line else 0.0
        node["ocr_label_type"] = best_line.get("label_type", "none") if best_line else "none"
        node["ocr_distance"] = best_distance if best_line else None
        node["ocr_association_score"] = score_label_confidence(
            best_distance,
            best_line["confidence"] if best_line else 0,
        )
        node["ocr_confidence_tier"] = classify_confidence(node.get("ocr_association_score", 0))

    return nodes


def attach_ocr_labels_to_edges(edges, nodes, ocr_lines):
    node_lookup = {node["id"]: node for node in nodes}

    for edge in edges:
        source = node_lookup[edge[0]]
        target = node_lookup[edge[2]]

        mid_x = (source["x"] + target["x"]) / 2
        mid_y = (source["y"] + target["y"]) / 2

        best = None
        best_distance = None
        for line in ocr_lines:
            dx = mid_x - line["x"]
            dy = mid_y - line["y"]
            distance = (dx * dx + dy * dy) ** 0.5

            if best_distance is None or distance < best_distance:
                best = line
                best_distance = distance

        edge_data = {
            "label": best["text"] if best else None,
            "confidence": best["confidence"] if best else 0,
            "distance": best_distance,
        }
        if edge_data["label"] and is_exit_command(edge_data["label"]):
            edge_data["is_command"] = True
        edge_data["confidence_tier"] = classify_confidence(
            score_label_confidence(edge_data["distance"], edge_data["confidence"])
        )

        yield (*edge, edge_data)


def _sample_has_path(img, source, target):
    pixels = img.load()
    width, height = img.size
    steps = int(max(abs(target["x"] - source["x"]), abs(target["y"] - source["y"])))
    if steps <= 2:
        return False

    hit_count = 0
    total_count = 0
    for step in range(2, steps - 1):
        ratio = step / steps
        sample_x = int(round(source["x"] + (target["x"] - source["x"]) * ratio))
        sample_y = int(round(source["y"] + (target["y"] - source["y"]) * ratio))
        seen = False
        for offset_x in (-1, 0, 1):
            for offset_y in (-1, 0, 1):
                cur_x = sample_x + offset_x
                cur_y = sample_y + offset_y
                if 0 <= cur_x < width and 0 <= cur_y < height:
                    red, green, blue = pixels[cur_x, cur_y]
                    if not (red > 245 and green > 245 and blue > 245):
                        seen = True
                        break
            if seen:
                break
        total_count += 1
        if seen:
            hit_count += 1

    return total_count > 0 and (hit_count / total_count) >= 0.6


def _candidate_direction(source, target):
    dx = target["x"] - source["x"]
    dy = target["y"] - source["y"]
    abs_x = abs(dx)
    abs_y = abs(dy)
    if abs_y <= 3 and 14 <= abs_x <= 60:
        return ("east" if dx > 0 else "west", abs_x)
    if abs_x <= 3 and 14 <= abs_y <= 60:
        return ("south" if dy > 0 else "north", abs_y)
    if abs(abs_x - abs_y) <= 3 and 14 <= abs_x <= 60:
        if dx > 0 and dy > 0:
            return ("southeast", (abs_x + abs_y) / 2)
        if dx > 0 and dy < 0:
            return ("northeast", (abs_x + abs_y) / 2)
        if dx < 0 and dy > 0:
            return ("southwest", (abs_x + abs_y) / 2)
        return ("northwest", (abs_x + abs_y) / 2)
    return (None, None)


def _derive_edges(img, nodes):
    edge_map = {node["id"]: {} for node in nodes}

    for source in nodes:
        candidates = {}
        for target in nodes:
            if source["id"] == target["id"]:
                continue
            direction, distance = _candidate_direction(source, target)
            if not direction:
                continue
            current = candidates.get(direction)
            if current is None or distance < current[0]:
                candidates[direction] = (distance, target)

        for direction, (_, target) in candidates.items():
            if _sample_has_path(img, source, target):
                edge_map[source["id"]][direction] = target["id"]

    symmetric_edges = []
    for source_id, exits in edge_map.items():
        for direction, target_id in exits.items():
            reverse_direction = OPPOSITE_DIRECTIONS[direction]
            target_exits = edge_map.get(target_id, {})
            if target_exits.get(reverse_direction) == source_id:
                symmetric_edges.append((source_id, direction, target_id))

    return symmetric_edges


def _build_adjacency(edges):
    adjacency = {}
    for source_id, direction, target_id in edges:
        adjacency.setdefault(source_id, {})[direction] = target_id
    return adjacency


def _collect_connected_components(nodes, edges):
    adjacency = _build_adjacency(edges)
    node_ids = [node["id"] for node in nodes]
    visited = set()
    components = []

    for node_id in node_ids:
        if node_id in visited:
            continue
        stack = [node_id]
        component = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            for target_id in adjacency.get(current, {}).values():
                if target_id not in visited:
                    stack.append(target_id)
        components.append(component)

    return components


def _distance_between(source, target):
    dx = target["x"] - source["x"]
    dy = target["y"] - source["y"]
    return (dx * dx + dy * dy) ** 0.5


def _sample_color_ratio(img, source, target, color):
    pixels = img.load()
    width, height = img.size
    steps = int(max(abs(target["x"] - source["x"]), abs(target["y"] - source["y"])))
    if steps <= 1:
        return 0.0

    hits = 0
    samples = 0
    for step in range(1, steps):
        ratio = step / steps
        sample_x = int(round(source["x"] + (target["x"] - source["x"]) * ratio))
        sample_y = int(round(source["y"] + (target["y"] - source["y"]) * ratio))
        if 0 <= sample_x < width and 0 <= sample_y < height:
            samples += 1
            if pixels[sample_x, sample_y] == color:
                hits += 1
    return (hits / samples) if samples else 0.0


def _choose_special_exit_name(source, target, img):
    source_region, _source_district = _region_for_position(source["x"], source["y"])
    target_region, _target_district = _region_for_position(target["x"], target["y"])
    water_ratio = _sample_color_ratio(img, source, target, BLUE_WATER)
    distance = _distance_between(source, target)

    candidates = []
    if water_ratio >= 0.18:
        if "Docks" in source_region or "Docks" in target_region:
            candidates.extend(["pier", "ferry", "dock", "bridge"])
        else:
            candidates.extend(["bridge", "ferry", "pier", "ramp"])

    if "Gate" in source_region or "Gate" in target_region:
        candidates.extend(["gate", "arch", "stair"])
    elif source["y"] < 220 or target["y"] < 220:
        candidates.extend(["arch", "gate", "stair"])
    elif distance > 120:
        candidates.extend(["path", "walk", "ramp"])
    else:
        candidates.extend(["path", "walk", "entry", "yard"])

    candidates.extend(SPECIAL_EXIT_NAME_CANDIDATES)
    deduped = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _choose_room_exit_name(preferred_names, used_names):
    for candidate in preferred_names:
        if candidate not in used_names:
            return candidate
    suffix = 2
    while True:
        for candidate in preferred_names:
            numbered = f"{candidate}{suffix}"
            if numbered not in used_names:
                return numbered
        suffix += 1


def _derive_special_edges(img, nodes, standard_edges):
    node_lookup = {node["id"]: node for node in nodes}
    components = _collect_connected_components(nodes, standard_edges)
    if len(components) <= 1:
        return []

    component_lookup = {}
    for index, component in enumerate(components):
        for node_id in component:
            component_lookup[node_id] = index

    edge_key = set()
    for source_id, _direction, target_id in standard_edges:
        edge_key.add(frozenset((source_id, target_id)))

    parents = list(range(len(components)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left, right):
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return False
        parents[right_root] = left_root
        return True

    candidate_links = []
    for left_index in range(len(components)):
        for right_index in range(left_index + 1, len(components)):
            best_pair = None
            for source_id in components[left_index]:
                source = node_lookup[source_id]
                for target_id in components[right_index]:
                    if frozenset((source_id, target_id)) in edge_key:
                        continue
                    target = node_lookup[target_id]
                    distance = _distance_between(source, target)
                    if best_pair is None or distance < best_pair[0]:
                        best_pair = (distance, source_id, target_id)
            if best_pair:
                candidate_links.append((best_pair[0], left_index, right_index, best_pair[1], best_pair[2]))

    candidate_links.sort(key=lambda item: item[0])
    used_names = {}
    special_edges = []
    for _distance, left_index, right_index, source_id, target_id in candidate_links:
        if not union(left_index, right_index):
            continue

        source = node_lookup[source_id]
        target = node_lookup[target_id]
        preferred = _choose_special_exit_name(source, target, img)
        source_used = used_names.setdefault(source_id, set())
        target_used = used_names.setdefault(target_id, set())
        source_name = _choose_room_exit_name(preferred, source_used)
        target_name = _choose_room_exit_name(preferred, target_used | {source_name})
        source_used.add(source_name)
        target_used.add(target_name)
        special_edges.append((source_id, source_name, target_id, target_name))

    return special_edges


def _collect_components(nodes, adjacency, allowed_directions, sort_key):
    node_ids = [node["id"] for node in nodes]
    visited = set()
    components = []

    for node_id in node_ids:
        if node_id in visited:
            continue
        neighbors = [adjacency.get(node_id, {}).get(direction) for direction in allowed_directions]
        if not any(neighbors):
            continue

        stack = [node_id]
        component = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            visited.add(current)
            for direction in allowed_directions:
                target_id = adjacency.get(current, {}).get(direction)
                if target_id and target_id not in component:
                    stack.append(target_id)

        components.append(sorted(component, key=sort_key))

    return components


def _next_road_name(stems, index, suffix):
    stem = stems[index % len(stems)]
    repeat = index // len(stems)
    if repeat:
        return f"{stem} {suffix} {repeat + 1}"
    return f"{stem} {suffix}"


def _position_label(order_index, size, axis):
    if size <= 1:
        return "Close"
    if axis == "vertical":
        labels = ["North Reach", "Upper Stretch", "Midway", "Lower Stretch", "South Reach"]
    elif axis == "horizontal":
        labels = ["West Reach", "Western Run", "Midway", "Eastern Run", "East Reach"]
    else:
        labels = ["Outer Bend", "Crook", "Kink", "Turn", "Inner Bend"]
    ratio = order_index / max(size - 1, 1)
    slot = min(int(ratio * len(labels)), len(labels) - 1)
    return labels[slot]


def _road_sort_key(node_lookup, axis):
    if axis == "vertical":
        return lambda node_id: (node_lookup[node_id]["y"], node_lookup[node_id]["x"])
    if axis == "horizontal":
        return lambda node_id: (node_lookup[node_id]["x"], node_lookup[node_id]["y"])
    return lambda node_id: (node_lookup[node_id]["y"], node_lookup[node_id]["x"])


def _build_road_metadata(nodes, edges):
    node_lookup = {node["id"]: node for node in nodes}
    adjacency = _build_adjacency(edges)
    node_meta = {node["id"]: {"street": None, "lane": None, "alley": []} for node in nodes}

    vertical_components = _collect_components(
        nodes,
        adjacency,
        {"north", "south"},
        _road_sort_key(node_lookup, "vertical"),
    )
    horizontal_components = _collect_components(
        nodes,
        adjacency,
        {"east", "west"},
        _road_sort_key(node_lookup, "horizontal"),
    )
    diagonal_components = _collect_components(
        nodes,
        adjacency,
        {"northeast", "northwest", "southeast", "southwest"},
        _road_sort_key(node_lookup, "diagonal"),
    )

    for index, component in enumerate(sorted(vertical_components, key=lambda comp: node_lookup[comp[0]]["x"])):
        road_type = "street" if len(component) >= 3 else "alley"
        suffix = "Street" if road_type == "street" else "Alley"
        road_name = _next_road_name(STREET_STEMS if road_type == "street" else ALLEY_STEMS, index, suffix)
        for order_index, node_id in enumerate(component):
            info = {
                "name": road_name,
                "type": road_type,
                "axis": "vertical",
                "position": _position_label(order_index, len(component), "vertical"),
                "size": len(component),
            }
            if road_type == "street":
                node_meta[node_id]["street"] = info
            else:
                node_meta[node_id]["alley"].append(info)

    for index, component in enumerate(sorted(horizontal_components, key=lambda comp: node_lookup[comp[0]]["y"])):
        road_type = "lane" if len(component) >= 3 else "alley"
        suffix = "Lane" if road_type == "lane" else "Alley"
        road_name = _next_road_name(LANE_STEMS if road_type == "lane" else ALLEY_STEMS, index, suffix)
        for order_index, node_id in enumerate(component):
            info = {
                "name": road_name,
                "type": road_type,
                "axis": "horizontal",
                "position": _position_label(order_index, len(component), "horizontal"),
                "size": len(component),
            }
            if road_type == "lane":
                node_meta[node_id]["lane"] = info
            else:
                node_meta[node_id]["alley"].append(info)

    diagonal_index = 0
    for component in sorted(diagonal_components, key=lambda comp: (node_lookup[comp[0]]["y"], node_lookup[comp[0]]["x"])):
        if len(component) >= 3:
            road_name = _next_road_name(ALLEY_STEMS, diagonal_index, "Alley")
            diagonal_index += 1
            for order_index, node_id in enumerate(component):
                info = {
                    "name": road_name,
                    "type": "alley",
                    "axis": "diagonal",
                    "position": _position_label(order_index, len(component), "diagonal"),
                    "size": len(component),
                }
                names = {entry["name"] for entry in node_meta[node_id]["alley"]}
                if info["name"] not in names:
                    node_meta[node_id]["alley"].append(info)

    for meta in node_meta.values():
        meta["alley"].sort(key=lambda info: (info["name"], info["position"]))

    return node_meta


def _region_for_position(x_pos, y_pos):
    for matcher, region_name, district in REGION_RULES:
        if matcher(x_pos, y_pos):
            return region_name, district
    return ("The Landing", "market")


def _room_key(node, road_meta):
    if node.get("final_label"):
        return node["final_label"]

    street = road_meta.get("street")
    lane = road_meta.get("lane")
    alleys = road_meta.get("alley", [])
    if street and lane:
        return f"{street['name']} and {lane['name']}"
    if street and alleys:
        return f"{street['name']} by {alleys[0]['name']}"
    if lane and alleys:
        return f"{lane['name']} by {alleys[0]['name']}"
    if street:
        return f"{street['name']}, {street['position']}"
    if lane:
        return f"{lane['name']}, {lane['position']}"
    if alleys:
        return f"{alleys[0]['name']}, {alleys[0]['position']}"
    region_name, _district = _region_for_position(node["x"], node["y"])
    return f"{region_name} [{node['x']},{node['y']}]"


def _room_desc(node, road_meta):
    if node.get("desc_final"):
        return node["desc_final"]

    area_name = node.get("area_name", "The Landing")

    region_name, district = _region_for_position(node["x"], node["y"])
    street = road_meta.get("street")
    lane = road_meta.get("lane")
    alleys = road_meta.get("alley", [])
    primary_position = None
    if street:
        primary_position = street["position"]
    elif lane:
        primary_position = lane["position"]
    elif alleys:
        primary_position = alleys[0]["position"]

    if street and lane:
        opening = INTERSECTION_OPENINGS[(node["x"] + node["y"]) % len(INTERSECTION_OPENINGS)].format(
            street=street["name"],
            lane=lane["name"],
        )
    elif street and alleys:
        opening = STREET_ALLEY_OPENINGS[(node["x"] + node["y"]) % len(STREET_ALLEY_OPENINGS)].format(
            street=street["name"],
            alley=alleys[0]["name"],
        )
    elif lane and alleys:
        opening = LANE_ALLEY_OPENINGS[(node["x"] + node["y"]) % len(LANE_ALLEY_OPENINGS)].format(
            lane=lane["name"],
            alley=alleys[0]["name"],
        )
    elif street:
        opening = STREET_OPENINGS[(node["x"] + node["y"]) % len(STREET_OPENINGS)].format(street=street["name"])
    elif lane:
        opening = LANE_OPENINGS[(node["x"] + node["y"]) % len(LANE_OPENINGS)].format(lane=lane["name"])
    elif alleys:
        opening = ALLEY_OPENINGS[(node["x"] + node["y"]) % len(ALLEY_OPENINGS)].format(alley=alleys[0]["name"])
    else:
        opening = f"This corner of {region_name} sits among the braided streets of {area_name}, ordinary only until you stop and take its measure."

    district_scene = DISTRICT_SCENES.get(district, DISTRICT_SCENES["market"])
    district_surface = DISTRICT_SURFACES.get(district, DISTRICT_SURFACES["market"])
    district_buildings = DISTRICT_BUILDINGS.get(district, DISTRICT_BUILDINGS["market"])
    district_sounds = DISTRICT_SOUNDS.get(district, DISTRICT_SOUNDS["market"])
    district_smells = DISTRICT_SMELLS.get(district, DISTRICT_SMELLS["market"])
    detail_line = district_scene[(node["x"] + node["y"]) % len(district_scene)]
    surface_line = district_surface[(node["x"] * 3 + node["y"]) % len(district_surface)]
    building_line = district_buildings[(node["x"] + node["y"] * 5) % len(district_buildings)]
    sound_line = district_sounds[(node["x"] * 7 + node["y"]) % len(district_sounds)]
    smell_line = district_smells[(node["x"] + node["y"] * 11) % len(district_smells)]
    marker_line = MARKER_SCENES.get(node["kind"], MARKER_SCENES["gray"])
    position_line = ""
    if primary_position and primary_position in POSITION_DETAILS:
        options = POSITION_DETAILS[primary_position]
        position_line = options[(node["x"] + node["y"] * 13) % len(options)]

    atmosphere_options = [detail_line, surface_line, building_line, sound_line, smell_line, marker_line]
    atmosphere_one = atmosphere_options[(node["x"] * 17 + node["y"]) % len(atmosphere_options)]
    atmosphere_two = atmosphere_options[(node["x"] + node["y"] * 19 + 3) % len(atmosphere_options)]

    if atmosphere_two == atmosphere_one:
        atmosphere_two = atmosphere_options[(node["x"] + node["y"] * 23 + 1) % len(atmosphere_options)]

    parts = [opening, position_line, atmosphere_one, atmosphere_two]
    return " ".join(part for part in parts if part)


def _classify_service_flags(node):
    text_parts = [
        node.get("final_label"),
        node.get("generated_name"),
        node.get("ocr_label"),
        node.get("label_candidate"),
        node.get("poi_anchor"),
        node.get("poi_exit_name"),
        node.get("landmark_flavor"),
        node.get("generated_desc"),
        node.get("desc_final"),
    ]
    combined = " ".join(str(part or "") for part in text_parts).lower()
    is_bank = any(token in combined for token in ("bank", "exchange", "depository", "clerk", "ledger"))
    is_vault = any(token in combined for token in ("vault", "strongroom", "depository"))
    if is_bank and any(token in combined for token in ("strongroom", "vault", "storage")):
        is_vault = True
    return is_bank, is_vault


def _ensure_room(node, road_meta, namespace):
    room = _get_tagged(node["id"], namespace["node_category"])
    if not room:
        room = create_object(ROOM_TYPECLASS, key=_room_key(node, road_meta))

    room.key = _room_key(node, road_meta)
    room.db.desc = _room_desc(node, road_meta)
    room.db.area = node.get("area_name", namespace["area_name"])
    room.db.is_stub = bool(node.get("is_stub"))
    if node.get("poi_anchor"):
        room.db.poi_anchor = node.get("poi_anchor")
    elif hasattr(room.db, "poi_anchor"):
        room.attributes.remove("poi_anchor")
    if node.get("poi_exit_name"):
        room.db.poi_exit_name = node.get("poi_exit_name")
    elif hasattr(room.db, "poi_exit_name"):
        room.attributes.remove("poi_exit_name")
    room.db.map_x = node["x"]
    room.db.map_y = node["y"]
    room.db.marker_kind = node["kind"]
    room.db.region_name = _region_for_position(node["x"], node["y"])[0]
    is_bank, is_vault = _classify_service_flags(node)
    room.db.is_bank = is_bank
    room.db.is_vault = is_vault
    if road_meta.get("street"):
        room.db.street_name = road_meta["street"]["name"]
    else:
        room.attributes.remove("street_name")
    if road_meta.get("lane"):
        room.db.lane_name = road_meta["lane"]["name"]
    else:
        room.attributes.remove("lane_name")
    room.db.alley_names = [entry["name"] for entry in road_meta.get("alley", [])]
    room.home = room.home or room
    room.aliases.add(f"{namespace['node_alias_prefix']}_{node['x']}_{node['y']}")
    room.tags.add(*namespace["area_tag"])
    room.tags.add(*namespace["area_version_tag"])
    room.tags.add(node["id"], category=namespace["node_category"])
    if is_bank:
        room.tags.add("bank")
    if is_vault:
        room.tags.add("vault")
    return room


def _ensure_exit(source_id, direction, source_room, target_room, namespace):
    exit_id = f"{source_id}:{direction}"
    exit_obj = _get_tagged(exit_id, namespace["exit_category"])
    if not exit_obj:
        exit_obj = create_object(
            EXIT_TYPECLASS,
            key=direction,
            aliases=DIR_ALIASES.get(direction, []),
            location=source_room,
            destination=target_room,
            home=source_room,
        )
    else:
        exit_obj.key = direction
        exit_obj.location = source_room
        exit_obj.destination = target_room
        exit_obj.home = source_room
        exit_obj.aliases.clear()
        for alias in DIR_ALIASES.get(direction, []):
            exit_obj.aliases.add(alias)

    exit_obj.tags.add(*namespace["area_tag"])
    exit_obj.tags.add(*namespace["area_version_tag"])
    exit_obj.tags.add(exit_id, category=namespace["exit_category"])
    return exit_obj


def _ensure_special_exit(source_id, exit_name, target_id, source_room, target_room, namespace, aliases=None):
    exit_id = f"{source_id}:special:{target_id}"
    exit_obj = _get_tagged(exit_id, namespace["exit_category"])
    if not exit_obj:
        exit_obj = create_object(
            EXIT_TYPECLASS,
            key=exit_name,
            location=source_room,
            destination=target_room,
            home=source_room,
        )
    else:
        exit_obj.key = exit_name
        exit_obj.location = source_room
        exit_obj.destination = target_room
        exit_obj.home = source_room
        exit_obj.aliases.clear()
    for alias in aliases or []:
        exit_obj.aliases.add(alias)

    exit_obj.tags.add(*namespace["area_tag"])
    exit_obj.tags.add(*namespace["area_version_tag"])
    exit_obj.tags.add(exit_id, category=namespace["exit_category"])
    return exit_obj


def extract_the_landing_area_spec(
    map_path=None,
    use_ocr=USE_OCR,
    use_ai_adjudication=USE_AI_ADJUDICATION,
    area_id="the_landing",
    profile=None,
    style_settings=None,
):
    namespace = area_namespace(area_id)
    map_path = Path(map_path) if map_path else MAP_PATH
    image = _load_map_image(map_path)
    nodes = _detect_nodes(image, area_slug=namespace["area_slug"])
    ocr_bundle = None
    ocr_lines = []
    if use_ocr:
        try:
            ocr_bundle = extract_ocr_bundle(map_path)
        except RuntimeError as exc:
            print(f"The Landing OCR disabled at runtime: {exc}")
        else:
            ocr_lines = ocr_bundle["lines"]
            attach_ocr_labels_to_nodes(nodes, ocr_lines)

    standard_edges = _derive_edges(image, nodes)
    special_edges = _derive_special_edges(image, nodes, standard_edges)
    enriched_standard_edges = list(attach_ocr_labels_to_edges(standard_edges, nodes, ocr_lines))
    enriched_special_edges = list(
        attach_ocr_labels_to_edges(
            [(source_id, exit_name, target_id) for source_id, exit_name, target_id, _reverse_name in special_edges],
            nodes,
            ocr_lines,
        )
    )
    all_edges = list(standard_edges)
    for source_id, exit_name, target_id, _reverse_name in special_edges:
        all_edges.append((source_id, exit_name, target_id))
    for source_id, _exit_name, target_id, reverse_name in special_edges:
        all_edges.append((target_id, reverse_name, source_id))

    road_meta = _build_road_metadata(nodes, standard_edges)
    for node in nodes:
        node["area_name"] = namespace["area_name"]
        node["generated_name"] = _room_key(dict(node), road_meta[node["id"]])
        node["road_meta"] = road_meta[node["id"]]
        node["prose_seed"] = {
            "district": _region_for_position(node["x"], node["y"])[1],
            "marker_kind": node.get("kind"),
        }
        node["generated_desc"] = _room_desc(dict(node), road_meta[node["id"]])

    artifact_edges = []
    for source_id, exit_name, target_id, edge_data in enriched_standard_edges:
        edge_meta = dict(edge_data)
        edge_meta["exit_type"] = "directional"
        artifact_edges.append((source_id, exit_name, target_id, edge_meta))

    reverse_special_lookup = {
        (target_id, reverse_name, source_id)
        for source_id, _exit_name, target_id, reverse_name in special_edges
    }

    for source_id, exit_name, target_id, edge_data in enriched_special_edges:
        edge_meta = dict(edge_data)
        edge_meta["exit_type"] = "special"
        artifact_edges.append((source_id, exit_name, target_id, edge_meta))

    for source_id, reverse_name, target_id in reverse_special_lookup:
        artifact_edges.append(
            (
                source_id,
                reverse_name,
                target_id,
                {
                    "exit_type": "special",
                    "final_exit_name": reverse_name,
                    "confidence": 0,
                    "distance": None,
                    "confidence_tier": "none",
                },
            )
        )
    area_spec = {
        "nodes": nodes,
        "edges": artifact_edges,
        "meta": {
            "ocr_used": bool(ocr_bundle),
            "node_count": len(nodes),
            "edge_count": len(all_edges),
            "area_id": area_id,
            "area_name": namespace["area_name"],
            "area_slug": namespace["area_slug"],
        },
    }
    if use_ai_adjudication:
        area_spec = adjudicate_area_spec(
            area_spec,
            context={
                "profile": profile or {},
                "area_id": area_id,
                "style": style_settings or {},
            },
        )

    if ocr_bundle:
        print(f"OCR lines found: {len(ocr_bundle['lines'])}")
        print(f"Special exit labels found: {len(ocr_bundle['special_exit_labels'])}")
        print(f"Place-name candidates found: {len(ocr_bundle['place_name_candidates'])}")

    return area_spec


def build_the_landing_from_area_spec(area_spec):
    namespace = area_namespace(area_spec["meta"]["area_id"])
    artifacts = artifact_paths(area_spec["meta"]["area_id"])
    nodes = [dict(node) for node in area_spec["nodes"]]
    road_meta = {
        node["id"]: node.get("road_meta", {"street": None, "lane": None, "alley": []})
        for node in nodes
    }
    valid_node_ids = {node["id"] for node in nodes}
    valid_exit_ids = set()
    for source_id, exit_name, target_id, edge_data in area_spec["edges"]:
        if edge_data.get("exit_type") == "special":
            valid_exit_ids.add(f"{source_id}:special:{target_id}")
        else:
            valid_exit_ids.add(f"{source_id}:{exit_name}")

    _cleanup_existing_area(valid_node_ids, valid_exit_ids, namespace)

    rooms = {node["id"]: _ensure_room(node, road_meta[node["id"]], namespace) for node in nodes}
    for source_id, exit_name, target_id, edge_data in area_spec["edges"]:
        final_exit_name = edge_data.get("final_exit_name", exit_name)
        if edge_data.get("exit_type") == "special":
            _ensure_special_exit(
                source_id,
                final_exit_name,
                target_id,
                rooms[source_id],
                rooms[target_id],
                namespace,
                aliases=edge_data.get("aliases", []),
            )
        else:
            _ensure_exit(source_id, final_exit_name, rooms[source_id], rooms[target_id], namespace)

    flags = generate_review_flags(nodes, area_spec["edges"])
    save_area_spec(artifacts["areaspec"], area_spec)
    save_review_report(artifacts["review"], flags)

    return {
        "rooms": rooms,
        "nodes": nodes,
        "edges": area_spec["edges"],
        "flags": flags,
        "artifacts": artifacts,
        "meta": area_spec["meta"],
    }


def build_the_landing(
    map_path=None,
    use_ocr=USE_OCR,
    use_ai_adjudication=USE_AI_ADJUDICATION,
    area_id="the_landing",
    profile=None,
    style_settings=None,
):
    area_spec = extract_the_landing_area_spec(
        map_path=map_path,
        use_ocr=use_ocr,
        use_ai_adjudication=use_ai_adjudication,
        area_id=area_id,
        profile=profile,
        style_settings=style_settings,
    )
    return build_the_landing_from_area_spec(area_spec)