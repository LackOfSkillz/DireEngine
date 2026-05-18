import json
import re
from pathlib import Path

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
AREA_NAME = "The Crossing"
CANONICAL_AREA_TAG = "canonical_crossing_phase1"
CANONICAL_AREA_TAG_PHASE2 = "canonical_crossing_phase2"
CANONICAL_AREA_TAG_PHASE3 = "canonical_crossing_phase3"
CANONICAL_AREA_TAG_PHASE4 = "canonical_crossing_phase4"
CANONICAL_AREA_TAG_PHASE5 = "canonical_crossing_phase5"
CANONICAL_AREA_TAG_PHASE6 = "canonical_crossing_phase6"
CANONICAL_ID_CATEGORY = "canonical_crossing_map_id"
ARRIVAL_ROOM_ID = 788
NEW_LANDING_AREA_NAME = "New Landing"
DEPRECATION_NOTE = "Procedural New Landing is deprecated in favor of phased canonical Crossing imports."
DEFAULT_MAP_PATH = Path(__file__).resolve().parents[3] / "data" / "canon" / "map-1777858104.json"

DIR_ALIASES = {
    "north": ["n"],
    "south": ["s"],
    "east": ["e"],
    "west": ["w"],
    "northeast": ["ne"],
    "northwest": ["nw"],
    "southeast": ["se"],
    "southwest": ["sw"],
    "up": ["u"],
    "down": ["d"],
    "out": ["o"],
}

PHASE1_ROOM_IDS = [
    728,
    729,
    733,
    752,
    753,
    766,
    767,
    776,
    783,
    785,
    786,
    787,
    788,
    789,
    790,
    791,
    792,
    793,
    794,
    796,
    836,
    847,
    848,
    862,
    906,
    910,
    954,
    6871,
    7902,
    7905,
]

PHASE1_ROOM_SPECS = {
    728: {"title": "Eastern Gate", "desc": "The eastern gate stands in weathered stone above a hard-used run of road, with gate traffic thinning just enough for the city's inner rhythm to take over. Old guardwork, wheel scars, and the first turn of Hodierna Way make the threshold feel practical rather than ceremonial."},
    729: {"title": "Hodierna Way", "desc": "Hodierna Way runs inward from the eastern gate beneath close-built facades and the steady foot traffic of people who know where they are headed. The street feels less grand than dependable, shaped by healing houses, errands, and the ordinary pressure of a living city."},
    733: {"title": "Alamhif Trace", "desc": "Alamhif Trace breaks from the denser streets in a rougher strip of earth and stone, as if the city briefly forgot to finish dressing the road. Even so, the place is worn into certainty by repeated boots, cart wheels, and the kind of traffic that values function over polish."},
    752: {"title": "Lunat Shade Road", "desc": "This reach of Lunat Shade Road lies lower and quieter than the Green, with road grit, damp mortar, and the muted sounds of nearby thresholds replacing the open square's bustle. The street feels like a working seam between better-known corners of town."},
    753: {"title": "Lunat Shade Road", "desc": "Lunat Shade Road narrows here into a more lived-in stretch where moss, road dust, and small discarded things gather against stonework that has seen long use. It reads as the back side of the Green's public face, close enough to the center to hear it and far enough away to avoid its performance."},
    766: {"title": "Champions' Square", "desc": "Champions' Square opens in disciplined paving and older civic stone, giving the block a public weight without turning it into ceremony. Traffic cuts across the square in practiced lines, the kind made by messengers, petitioners, and people used to choosing quickly."},
    767: {"title": "Clanthew Boulevard", "desc": "Clanthew Boulevard pushes west from the square in a broad, self-assured line of stone and frontage, busy enough to feel important but too workmanlike to become pretty. The boulevard carries the energy of a place that feeds larger institutions without needing to announce itself."},
    776: {"title": "Trollferry Quay", "desc": "Trollferry Quay leans toward the river in wet stone, salt air, and the patient wear of freight handled day after day. The quay feels narrow in the way working waterfronts often do, built to keep goods moving rather than people lingering."},
    783: {"title": "Asemath Walk", "desc": "Asemath Walk threads near the Green with enough open movement to stay public and enough scuffing underfoot to feel well used. The street holds together as a crossroads of errands, shoppers, and locals who cut through without ever seeming lost."},
    785: {"title": "Manciple Cobble", "desc": "Manciple Cobble is a short hard-used lane where the paving looks repaired more often than admired. It feels like a serviceable edge-piece of the district, the kind of road that matters because it keeps the busier places connected."},
    786: {"title": "Via Iltesh", "desc": "Via Iltesh climbs into a simpler run of stone bordered by walls and everyday frontage, with fewer pauses built into it than the Green allows. The way is direct and slightly stern, as though it expects travelers to keep moving."},
    787: {"title": "Via Iltesh", "desc": "This segment of Via Iltesh sits close to the Green without sharing its breathing room, carrying traffic between tighter corners of the district on a road scuffed by constant passage. Bits of dust, grit, and worn stone make the route feel practical and old."},
    788: {"title": "Town Green North", "desc": "The northern reach of Town Green opens in a broad spread of grass and stone walks where the city finally gives itself room to breathe. Trees, benches, and the draw of the pond soften the square, but the traffic around its edges keeps the place tied firmly to the Crossing's daily pulse."},
    789: {"title": "Town Green Northwest", "desc": "Town Green Northwest feels greener and slightly more sheltered than the road-fed edges of the square, with thicker shade and a quieter turn to the traffic. The city still presses close, but here it does so with softer shoes and less urgency."},
    790: {"title": "Puddle Path", "desc": "Puddle Path trails away from the Green in a damp, narrow cut where runoff and foot traffic have taught the ground to hold its own weather. It feels like a small local way known best by those who use it often."},
    791: {"title": "Town Green Southwest", "desc": "The southwest corner of the Green carries more of the city's worn edges into the open lawn, where grass meets tracked dirt and the nearby roads feel close enough to re-enter at once. Even so, the square still manages a pocket of ease here."},
    792: {"title": "Town Green South", "desc": "Town Green South sits where the open square gives way to busier approaches, making this stretch feel like both gathering place and thoroughfare. The paving is more worn, the paths more contested, and the sense of movement stronger than in the greener corners."},
    793: {"title": "Town Green Southeast", "desc": "The southeast corner of the Green feels lively and a little untidy, with flowers, public clutter, and the sense that people pass through here carrying more plans than time. It is one of the square's more social edges, where open ground gives way to destination traffic."},
    794: {"title": "Town Green Northeast", "desc": "Town Green Northeast looks toward the marketward pull of the Crossing, where the square's softer edges give way to more deliberate movement. Grass and older trees still hold the center together, but nearby routes make this corner feel alert and transitional."},
    796: {"title": "Cheopman Lane", "desc": "Cheopman Lane peels away from the market side in a narrow practical strip where the city feels close enough to touch on both sides. It reads as a local connector more than a promenade, useful because it gets you somewhere without fuss."},
    836: {"title": "Smithy Lane", "desc": "Smithy Lane carries the harder smell of heated work and worn paving, with the sense that craft and delivery traffic matter here as much as ordinary foot travel. The lane is modest in width but stubborn in purpose."},
    847: {"title": "Landfall Dock", "desc": "Landfall Dock sits in the blunt practical air of the waterfront, where damp timber, worked rope, and cargo noise strip any romance from arrival by water. The dock feels built to receive weight, weather, and people who seldom have time to stare."},
    848: {"title": "Landfall Jetty", "desc": "The jetty reaches into the water on worn boards and salt-stiff fittings, more exposed than the dock behind it and more honest about the river's mood. Wind and spray do part of the talking here."},
    862: {"title": "Oxenwaithe Bridge", "desc": "Oxenwaithe Bridge carries road traffic above the water with the confidence of older stonework built to endure noise, weather, and impatience. From the span, the Crossing feels divided into currents of trade, travel, and river labor all at once."},
    906: {"title": "Nightrunner's Quay", "desc": "Nightrunner's Quay is a narrower river edge where the work feels quicker, quieter, and slightly less public than the broader docks. The place gives the impression of cargo and conversations both moving on tight schedules."},
    910: {"title": "Gold Barque Quay", "desc": "Gold Barque Quay spreads in damp stone and river smell beneath the sort of traffic that measures time by unloading and departure. It feels better trafficked than hidden, but no less ruled by labor for that."},
    954: {"title": "Mongers' Bazaar", "desc": "Mongers' Bazaar gathers the market's louder instincts into a tighter, noisier knot where bargaining, display, and opportunism all compete for the same breath of air. The square feels active even when no one person is doing anything dramatic."},
    6871: {"title": "Town Green Pond", "desc": "The pond lies as the Green's quiet center, where water, reeds, and slower sounds interrupt the harder tempo of the surrounding streets. Even here the Crossing stays nearby, but the water persuades people to lower their voices before they notice they have done it."},
    7902: {"title": "Fostra Square", "desc": "Fostra Square holds a smaller civic pause within the city, less open than the Green and more formal in how it gathers nearby routes. The space feels useful for meetings, passing orders, and the sort of business that prefers a little room around it."},
    7905: {"title": "Mongers' Square", "desc": "Mongers' Square sits just off the bazaar in a busier knot of trade where the paving has been worn by repeated setup, breakdown, and negotiation. It feels like the market's overflow memory made permanent in stone."},
}

PHASE2_ROOM_IDS = [
    730,
    746,
    759,
    760,
    763,
    764,
    765,
    768,
    771,
    772,
    795,
    819,
    822,
    849,
    863,
    864,
    889,
    891,
    904,
    905,
    907,
    908,
    909,
    911,
    912,
    924,
    925,
    926,
    945,
    946,
    13493,
    13494,
]

PHASE3_ROOM_IDS = [
    769,
    770,
    731,
    732,
    773,
    901,
    903,
    779,
    782,
    784,
    913,
    798,
    927,
    14712,
    810,
    813,
    944,
    820,
    837,
    734,
    865,
    744,
    747,
    751,
    758,
    888,
    762,
    13051,
    892,
    893,
    890,
    774,
    780,
]

PHASE4_ROOM_IDS = [
    838,
    839,
    843,
    844,
    845,
    756,
    757,
    761,
    816,
    799,
    800,
    801,
    817,
    807,
    808,
    811,
    812,
    16505,
    16506,
    16507,
    745,
    824,
    825,
    748,
    749,
    750,
    802,
    814,
    815,
    803,
    804,
    805,
    840,
    841,
    846,
    873,
    874,
    875,
    877,
    878,
    879,
    881,
    882,
    883,
    885,
    919,
    920,
    867,
    868,
    869,
    870,
    871,
    872,
    876,
    880,
    884,
    5752,
    5753,
    5754,
    5755,
    5756,
    5772,
    5773,
    5774,
    5775,
    5776,
    5777,
    5778,
    5779,
    754,
    821,
]

PHASE5_ROOM_IDS = [
    899,
    915,
    916,
    917,
    918,
    923,
    930,
    826,
    827,
    828,
    829,
    830,
    831,
    832,
    16508,
    16509,
    16510,
    16511,
    16512,
    16513,
    13586,
    13587,
    13588,
    13589,
    13590,
    13591,
    948,
    949,
    950,
    951,
    952,
    953,
    947,
    739,
    741,
]

PHASE6_ROOM_IDS = [
    735,
    736,
    737,
    738,
    740,
    742,
    743,
    755,
    775,
    777,
    778,
    781,
    797,
    809,
    818,
    842,
    866,
    886,
    887,
    894,
    895,
    896,
    897,
    898,
    900,
    902,
    914,
    921,
    922,
    928,
    929,
    957,
    8235,
]

PHASE2_ROOM_SPECS = {
    730: {"title": "Hodierna Way", "desc": "This stretch of Hodierna Way feels more hemmed in than the gateward end, with walls, thresholds, and habitual traffic keeping the road in a narrow working rhythm. The street carries the mood of somewhere people cross often without ever quite yielding it their attention."},
    746: {"title": "Dafora Row", "desc": "Dafora Row runs with the stubborn practicality of a side street that has grown useful by surviving other plans. Doors open straight onto the road, paving stays uneven, and the whole row feels lived in more than maintained."},
    759: {"title": "Trothfang Street", "desc": "Trothfang Street leans into trade traffic and older stone, with enough width for movement but not enough grace to make the motion feel easy. The road reads as a hard-used seam between busier civic corners."},
    760: {"title": "Trothfang Street", "desc": "Here Trothfang Street feels slightly rougher and more compressed, with scuffed stone and crowded frontage tightening the flow of people along it. The place has the blunt energy of a route that matters because it connects more important ones."},
    763: {"title": "Magen Road", "desc": "Magen Road runs in a steady, unsentimental line where storefronts and workrooms sit close to the paving and leave little room for ornament. The street feels ordinary in the dependable way that keeps a city functioning."},
    764: {"title": "Magen Road", "desc": "This reach of Magen Road carries the same workday pulse as the rest, but with heavier signs of carts, deliveries, and repeated foot traffic wearing at the edges. It feels like a route people trust even if they never admire it."},
    765: {"title": "Flamethorn Way", "desc": "Flamethorn Way breaks from the denser roads with a slightly sharper, more residential feel, though the city never loosens its hold completely. The lane is quieter, but not calm enough to stop being part of the Crossing's machinery."},
    768: {"title": "Clanthew Boulevard", "desc": "This farther run of Clanthew Boulevard keeps its civic confidence without any need for decoration, relying instead on breadth, old stone, and a constant stream of purposeful movement. It feels like a place the city expects people to take seriously."},
    771: {"title": "Clanthew Boulevard", "desc": "Clanthew Boulevard broadens here into a corridor of frontage, foot traffic, and institutional gravity, all of it worn smooth by repetition rather than grandeur. The boulevard has the settled authority of a road that serves large concerns daily."},
    772: {"title": "Clanthew Boulevard", "desc": "At this end Clanthew Boulevard begins to feel more transitional, feeding traffic onward while still holding its broad urban posture. The road is too busy to linger in and too established to ignore."},
    795: {"title": "Cheopman Lane", "desc": "Cheopman Lane narrows into a tighter market-side connector where walls and awnings seem to press closer over the paving. The lane feels built for passing through with purpose, not for stopping to decide anything."},
    819: {"title": "Truffenyi Place", "desc": "Truffenyi Place opens with just enough breathing room to suggest a square without fully escaping the streets around it. The space feels civic in use rather than scale, a pocket where errands, appointments, and short conversations collect."},
    822: {"title": "Truffenyi Place", "desc": "This side of Truffenyi Place holds the same public character, though the edges feel more worn and more directly claimed by nearby traffic. It is the kind of place where people meet because it is convenient, not because it is beautiful."},
    849: {"title": "Winding Wooden Stairs", "desc": "The wooden stairs climb in weathered turns above the dockside works, every tread shaped by damp, use, and the river air. They feel more like a practical concession to height than any attempt at comfort."},
    863: {"title": "Goodwhate Pike", "desc": "Goodwhate Pike takes the bridge traffic and turns it into a city street again, with wagon scars, shouted coordination, and the pressure of goods moving inland. The road feels commercially important even when nothing dramatic is happening on it."},
    864: {"title": "Goodwhate Pike", "desc": "This reach of Goodwhate Pike keeps the same trade-fed momentum, but with slightly tighter frontage and a more enclosed feel as the city closes around the road. Its importance shows in use rather than display."},
    889: {"title": "Varlet's Run", "desc": "Varlet's Run is a lean, quick sort of street where the paving stays busy and nobody seems inclined to block it for long. The place feels more like a channel for errands than a destination in its own right."},
    891: {"title": "Damaris Lane", "desc": "Damaris Lane threads away from the heavier routes in a quieter strip of stone and close-built walls, giving the impression of a local way that still answers to larger city currents. It feels tucked aside, but not forgotten."},
    904: {"title": "Damaris Lane", "desc": "This stretch of Damaris Lane feels tighter and more enclosed, with the sort of worn thresholds and wall-shadowed paving that suggest constant use at a smaller scale. The lane carries private routines more than public spectacle."},
    905: {"title": "Varlet's Run", "desc": "Farther along, Varlet's Run keeps its brisk, narrow character, with enough turn and interruption to make the traffic feel improvised even when it clearly is not. It is a street that rewards already knowing where you are going."},
    907: {"title": "Water Sprite Way", "desc": "Water Sprite Way stays close to the river mood without dropping fully into dock labor, carrying damp air and a faint waterfront restlessness through a tighter urban lane. The street feels transitional, as if pulled in two directions at once."},
    908: {"title": "Bank Street", "desc": "Bank Street has the scrubbed, deliberate air of a road tied to money and recordkeeping, where even ordinary foot traffic seems to move with slightly more restraint. The paving looks maintained because disorder would be noticed here."},
    909: {"title": "Bank Street", "desc": "This reach of Bank Street feels equally disciplined, though the closeness of doors and windows lends it a more watchful tone. It is the sort of street where small mistakes may linger in memory longer than elsewhere."},
    911: {"title": "Drayhorse Trace", "desc": "Drayhorse Trace is marked by hauling work in every visible surface, from wheel-cut stone to rubbed corners and lingering smells of harness and freight. The road feels strong-backed rather than elegant."},
    912: {"title": "Mercantile Street", "desc": "Mercantile Street carries business openly, with signs, foot traffic, and the low pressure of transaction making the road feel busy even in its quieter moments. It has the commercial self-awareness of a place built to be useful first."},
    924: {"title": "Drayhorse Trace", "desc": "This farther section of Drayhorse Trace narrows the same freight energy into a more confined run, where labor shows in the road itself more clearly than in any decoration. It feels like a street shaped by weight and repetition."},
    925: {"title": "3 Retainers' Crescent", "desc": "The crescent bends through the district with a slightly more mannered feel than the trade roads around it, though the stone underfoot still shows ordinary use. It reads as a quieter urban pocket rather than a retreat from the city."},
    926: {"title": "3 Retainers' Crescent", "desc": "Farther along the crescent, the curve and the enclosing walls make the road feel more private without ever becoming secluded. The place carries a calmer tone, but it remains firmly inside the Crossing's daily motion."},
    945: {"title": "Bazaar Walkway", "desc": "Bazaar Walkway compresses market movement into a narrower passage where stalls, voices, and quick judgments crowd close to the same strip of paving. The whole way feels designed to keep you moving while tempting you to stop."},
    946: {"title": "Bazaar Walkway", "desc": "This segment of Bazaar Walkway is just as crowded in spirit, with awnings, display space, and passing shoulders all competing for room. It feels lively in the specifically commercial sense that can turn into chaos if left unattended."},
    13493: {"title": "The Back Lawn", "desc": "The back lawn behind the amphitheater opens in a softer pocket of grass and trampled paths, where the city's harder edges ease without disappearing. Even here, the feeling is less pastoral than civic, as though leisure has been granted a controlled corner."},
    13494: {"title": "The Seating Area", "desc": "The amphitheater seating area gathers benches, sightlines, and the memory of public attention into a space meant for watching as much as speaking. It feels quieter between events, but never empty of expectation."},
}

PHASE3_ROOM_SPECS = {
    769: {"title": "Clanthew Boulevard", "desc": "This section of Clanthew Boulevard keeps the same broad civic posture as the squareward stretches, but the flow feels more transitional here, with side streets and enclosed courtyards pulling traffic off in quick decisions."},
    770: {"title": "Clanthew Boulevard", "desc": "Farther along, the boulevard feels like a hinge between public frontage and more private compounds, with the street still carrying confidence even as gates and branching routes start to interrupt its line."},
    731: {"title": "Hodierna Way", "desc": "Hodierna Way broadens slightly here without losing its practical city pressure, the stone underfoot worn by a steady mix of local errands, deliveries, and people cutting between busier destinations."},
    732: {"title": "Hodierna Way", "desc": "This western reach of Hodierna Way feels more tucked into the surrounding blockwork, with crossing foot traffic and narrow turnoffs making the street read as a dependable connector rather than a place to linger."},
    773: {"title": "Sirenberry Row", "desc": "Sirenberry Row runs with a quieter, more residential tone than the boulevard above it, though the Crossing never quite lets the place become calm. Doors, walls, and passing steps keep the street grounded in routine use."},
    901: {"title": "Bank Street", "desc": "This bend of Bank Street feels orderly to the point of restraint, with maintained stone, controlled frontage, and the sense that commerce here depends as much on credibility and memory as on simple traffic."},
    903: {"title": "Water Sprite Way", "desc": "Water Sprite Way carries a damp riverward edge through tighter city masonry, the lane feeling caught between mercantile order and the restlessness of nearby quays and back routes."},
    779: {"title": "Trollferry Approach", "desc": "Trollferry Approach draws traffic toward the ferryward edge of the district with the purposeful feel of a road people use because it goes somewhere necessary, not because it offers any comfort on the way."},
    782: {"title": "Lorethew Street", "desc": "Lorethew Street bends through the district with a more local scale than the boulevard grid around it, the paving and close frontage giving it the feel of a street that serves nearby lives first."},
    784: {"title": "Asemath Walk", "desc": "This farther stretch of Asemath Walk keeps the public ease of the Green-adjacent segment while narrowing into a more ordinary city lane, useful because it continues the flow rather than because it announces itself."},
    913: {"title": "Mercantile Street", "desc": "Mercantile Street presses commerce out into the open with signs, thresholds, and constant passing business, carrying the dry, practiced energy of a road that expects transactions to keep moving."},
    798: {"title": "Via Mandroga", "desc": "Via Mandroga feels narrower and more self-contained than the surrounding trade roads, a straight practical run of paving where service doors and private routines sit close behind the visible city face."},
    927: {"title": "3 Retainers' Crescent", "desc": "This farther turn of the crescent keeps its slightly more mannered tone, though the curve still belongs firmly to the Crossing, shaped more by repetition, walls, and foot traffic than by any quiet luxury."},
    14712: {"title": "Entrance", "desc": "The entrance stands as a threshold space rather than a street proper, where the city pauses long enough to frame an approach before giving way again to enclosed passages and controlled movement."},
    810: {"title": "Truffenyi Place", "desc": "This edge of Truffenyi Place feels more connected to the surrounding lanes than the squareward center, with inns, stable traffic, and converging routes making the space read as a busy junction in public disguise."},
    813: {"title": "Flamethorn Way", "desc": "Flamethorn Way turns quieter here, though only by comparison to the surrounding market and bridge-fed streets. The lane feels residential in scale, but still thoroughly claimed by the city around it."},
    944: {"title": "Bazaar Walkway", "desc": "This approach into the bazaar compresses movement into a ramped commercial seam where every few steps seem to offer another decision, another distraction, or another reason to be jostled aside."},
    820: {"title": "Sicle Grove Lane", "desc": "Sicle Grove Lane sits just off the broader public square with a more enclosed, local character, the kind of lane where storage doors, side entrances, and habitual shortcuts matter more than display."},
    837: {"title": "Smithy Lane", "desc": "This farther run of Smithy Lane stays marked by trade labor and heated work, with the paving carrying the evidence of carts, tools, and repeated hauling between nearby shops and yards."},
    734: {"title": "Alamhif Trace", "desc": "Farther along, Alamhif Trace keeps its rougher, functional mood, a road that feels slightly underfinished compared with the more civic streets nearby but no less certain in daily use."},
    865: {"title": "Goodwhate Pike", "desc": "This continuation of Goodwhate Pike keeps freight and bridge traffic in motion through a more enclosed city run, with the road's importance expressed through wear, noise, and repetition rather than width."},
    744: {"title": "Gull's View Terrace", "desc": "Gull's View Terrace carries a faintly elevated, river-facing mood without losing its utilitarian footing, the place feeling like a hard-used edge street that happens to catch more air than most."},
    747: {"title": "Dafora Row", "desc": "This farther stretch of Dafora Row feels even more local and lived-in, with close-built thresholds and patched stonework making the street read as an everyday service lane shaped by persistence."},
    751: {"title": "Albreda Boulevard", "desc": "Albreda Boulevard widens into a more deliberate urban run, its greater width and cleaner line suggesting importance while the steady foot traffic keeps it firmly in the realm of practical city movement."},
    758: {"title": "Trothfang Street", "desc": "This section of Trothfang Street feels like a working hinge between broader roads, with scuffed stone and branching routes turning the street into a place of constant directional choice."},
    888: {"title": "Varlet's Run", "desc": "Varlet's Run begins with the same quick, narrow character it keeps farther south, a lane better suited to fast errands and familiar shortcuts than to any kind of public pause."},
    762: {"title": "Magen Road", "desc": "This branch of Magen Road feels more transitional than the main commercial spine, carrying traffic between adjoining streets and private entrances with the same dependable lack of ornament."},
    13051: {"title": "Grey Raven Commissary", "desc": "The commissary feels more enclosed and purposeful than the streets outside, a thresholded service space whose importance lies in provisioning and controlled access rather than in any public-facing identity."},
    892: {"title": "Damaris Lane", "desc": "This northern reach of Damaris Lane stays close and somewhat private in tone, with the lane shaped by repeated local use and the sense that most people here already know where the next turn leads."},
    893: {"title": "Dodgers' Row", "desc": "Dodgers' Row narrows into a sharper, less reputable-feeling seam of the district, where the lane's cramped proportions and side exits suggest speed, familiarity, and an aversion to scrutiny."},
    890: {"title": "Cutpurse Alley", "desc": "Cutpurse Alley is a tight, quick little channel between better-known streets, carrying the kind of furtive energy that comes from cramped space, fast decisions, and routes chosen for convenience over comfort."},
    774: {"title": "Lorethew Street", "desc": "This stretch of Lorethew Street ties the Sirenberry side of the district into the ferryward lanes, keeping the same smaller-scale, neighborhood feel while serving as a real connector between busier roads."},
    780: {"title": "Lorethew Street", "desc": "Lorethew Street narrows into a short linking segment here, almost more hinge than street, but still marked by the same lived-in paving and local traffic that define the rest of the road."},
}

PHASE4_ROOM_SPECS = {
    838: {"title": "Smithy Lane", "desc": "This farther stretch of Smithy Lane stays close to forge work and hauling traffic, with the paving marked more by repeated labor than by any attempt at polish."},
    839: {"title": "Smithy Lane", "desc": "Smithy Lane narrows here into a workmanlike run of stone and soot where traffic feels driven by craft, errands, and delivery rather than by leisure."},
    843: {"title": "Smithy Lane", "desc": "The lane keeps its hard-used shopfront character, with heat, wear, and practical movement giving the street more weight than width."},
    844: {"title": "Smithy Lane", "desc": "Here Smithy Lane feels tighter and more enclosed, a short practical seam where the district's trade energy presses close against the walls."},
    845: {"title": "Smithy Lane", "desc": "At the far end, Smithy Lane still reads as a working street first, with every surface suggesting tools, transport, and long routine use."},
    756: {"title": "Oralana Ramble", "desc": "Oralana Ramble bends away from the busier streets in a quieter, more residential register, though the Crossing's everyday pressure never fully releases it."},
    757: {"title": "Oralana Ramble", "desc": "This middle run of Oralana Ramble feels modest and lived-in, shaped by repeated local movement rather than by any grand civic ambition."},
    761: {"title": "Oralana Ramble", "desc": "The ramble narrows into a more intimate lane here, with close frontage and habitual foot traffic giving the street a settled neighborhood feel."},
    816: {"title": "Oralana Ramble", "desc": "Farther along, Oralana Ramble keeps the same local tone, a quiet connector whose value comes from steady use rather than attention."},
    799: {"title": "Firulf Vista", "desc": "Firulf Vista opens a little more than the streets below it, but the district still feels urban and practical rather than scenic despite the name."},
    800: {"title": "Firulf Vista", "desc": "This stretch of Firulf Vista feels orderly and residential, with enough breathing room to soften the block without ever leaving the city's rhythm behind."},
    801: {"title": "Firulf Vista", "desc": "Firulf Vista continues as a compact neighborhood run where routine traffic and close stonework matter more than ornament or display."},
    817: {"title": "Firulf Vista", "desc": "At this end the vista works like a small hinge between lanes, stairs, and side streets, busy in quiet ways that suggest constant familiar use."},
    807: {"title": "Gildleaf Circle", "desc": "Gildleaf Circle feels calmer than the heavier trade roads nearby, but its curve and contained scale still belong firmly to the Crossing's daily life."},
    808: {"title": "Gildleaf Circle", "desc": "This central reach of Gildleaf Circle gathers a few side destinations into one contained turn of road, making the place feel local rather than hidden."},
    811: {"title": "Gildleaf Circle", "desc": "The circle narrows here into a quieter segment of paving and frontage, more domestic in tone but still threaded into the city around it."},
    812: {"title": "Gildleaf Circle", "desc": "Farther along, Gildleaf Circle keeps its compact residential mood while feeding traffic back into the busier roads at its edges."},
    16505: {"title": "Tatting Street", "desc": "Tatting Street threads through the district as a narrow, workaday passage where every turn seems built for local knowledge and short purposeful trips."},
    16506: {"title": "Tatting Street", "desc": "The street tightens into a brisk little run of paving here, with the kind of traffic that feels habitual, efficient, and slightly private."},
    16507: {"title": "Tatting Street", "desc": "At its far end, Tatting Street still feels like a small local seam, more about connection and familiarity than any public prominence."},
    745: {"title": "Riverpine Way", "desc": "Riverpine Way carries a faint riverward openness without losing its city footing, the lane feeling practical even where it catches a little extra air."},
    824: {"title": "Riverpine Way", "desc": "This middle stretch of Riverpine Way feels transitional and slightly tucked aside, shaped by small turns and repeated local passage."},
    825: {"title": "Riverpine Way", "desc": "Farther along, Riverpine Way becomes a compact connector between neighboring lanes, modest in scale but clearly important to the district around it."},
    748: {"title": "Betany Street", "desc": "Betany Street runs with a clean practical line through the block, useful less for spectacle than for how directly it links nearby streets."},
    749: {"title": "Betany Street", "desc": "The street keeps a steady local rhythm here, with stone, thresholds, and passing errands giving it the feel of a dependable neighborhood road."},
    750: {"title": "Betany Street", "desc": "At this end Betany Street feels more transitional, handing traffic onward without losing its modest residential character."},
    802: {"title": "Herald Street", "desc": "Herald Street holds a slightly more formal bearing than the surrounding lanes, though its importance still shows through routine use rather than grandeur."},
    814: {"title": "Herald Street", "desc": "This farther stretch of Herald Street reads as a narrow civic connector, a place where messages and ordinary movement would naturally cross."},
    815: {"title": "Herald Street", "desc": "At its quiet end, Herald Street stays composed and useful, with just enough dignity to stand apart from purely utilitarian lanes."},
    803: {"title": "Eylhaar Bane Road", "desc": "Eylhaar Bane Road feels older and more deliberate than some of the side streets around it, a sturdy road whose odd name suits its stronger character."},
    804: {"title": "Eylhaar Bane Road", "desc": "This middle run of the road carries several turnoffs without losing its own identity, staying broad-backed and practical under steady traffic."},
    805: {"title": "Eylhaar Bane Road", "desc": "Farther along, Eylhaar Bane Road feels like a hinge between smaller circles and larger routes, important because it keeps the district connected."},
    840: {"title": "Crofton Walk", "desc": "Crofton Walk cuts through the district with a lighter feel than the heavier trade roads, but it still serves as a hard-used urban connector."},
    841: {"title": "Crofton Walk", "desc": "This quieter stretch of Crofton Walk feels local and serviceable, a short run of paving meant more for passage than pause."},
    846: {"title": "Crofton Walk", "desc": "At the far end, Crofton Walk still reads as a practical side route, modest in width but important for how it ties nearby streets together."},
    873: {"title": "Swithen's Court", "desc": "Swithen's Court feels enclosed and somewhat private, a short court whose repeated use has given it certainty without ever making it grand."},
    874: {"title": "Swithen's Court", "desc": "This middle stretch of the court carries the same tucked-away tone, with close walls and familiar traffic shaping the space more than architecture does."},
    875: {"title": "Swithen's Court", "desc": "At the end of the court, the paving and silence feel more self-contained, though the city is still only a turn away."},
    877: {"title": "Inkhorne Street", "desc": "Inkhorne Street has a slightly ink-stained, trade-adjacent character, a narrow street that suggests clerks, recordkeeping, and ordinary business."},
    878: {"title": "Inkhorne Street", "desc": "This middle run of Inkhorne Street feels compact and watchful, with the sort of close frontage that remembers who passes through."},
    879: {"title": "Inkhorne Street", "desc": "Farther along, the street remains tight and practical, a small urban seam shaped by routine work rather than display."},
    881: {"title": "Elmod Close", "desc": "Elmod Close is a short, contained lane with a slightly sheltered feel, more local in tone than the through-streets around it."},
    882: {"title": "Elmod Close", "desc": "This central stretch of Elmod Close stays narrow and self-contained, its quiet use giving the road a settled neighborhood identity."},
    883: {"title": "Elmod Close", "desc": "At the far end, Elmod Close feels almost like a tucked-away pocket of the district, though it still belongs unmistakably to the Crossing."},
    885: {"title": "Lemicus Square", "desc": "Lemicus Square opens just enough to feel civic, gathering nearby approaches into a small public pause without losing the city's commercial pressure."},
    919: {"title": "Lemicus Square", "desc": "This side of the square feels more like a busy junction than a place of rest, with multiple approaches feeding directly into one another."},
    920: {"title": "Lemicus Square", "desc": "Farther around, Lemicus Square keeps its modest public character, a little knot of paving that organizes nearby movement more than it adorns it."},
    867: {"title": "Kertigen Road", "desc": "Kertigen Road begins as a firm north-south run of stone and traffic, broad enough to feel important and plain enough to stay honest about its work."},
    868: {"title": "Kertigen Road", "desc": "This stretch of Kertigen Road carries the same steady through-traffic, a practical urban artery shaped more by repetition than by ornament."},
    869: {"title": "Kertigen Road", "desc": "The road keeps a strong-backed, purposeful line here, with enough wear in the paving to show how constantly it is used."},
    870: {"title": "Kertigen Road", "desc": "At this busier reach, Kertigen Road feels like a hinge between adjoining districts, taking side traffic without surrendering its own importance."},
    871: {"title": "Kertigen Road", "desc": "This farther stretch stays direct and unsentimental, a road people trust because it carries them onward with little ceremony."},
    872: {"title": "Kertigen Road", "desc": "Here Kertigen Road feels heavier with cross traffic, its intersections making the street read as a true spine of the surrounding blocks."},
    876: {"title": "Kertigen Road", "desc": "This junction on Kertigen Road is busier and more contested, with several directions feeding through a road that still holds the district together."},
    880: {"title": "Kertigen Road", "desc": "Farther south, Kertigen Road narrows only slightly in feel, keeping its status as a major connector between adjacent courts and squares."},
    884: {"title": "Kertigen Road", "desc": "At its lower reach, Kertigen Road still feels established and weight-bearing, a road built to absorb traffic rather than impress it."},
    5752: {"title": "Entrance Hall", "desc": "The temple's entrance hall feels ceremonial without becoming grandiose, a circular threshold where hush and movement are both carefully controlled."},
    5753: {"title": "Hallway", "desc": "This temple hallway curves in a quiet, deliberate circuit, more concerned with ritual order and enclosed movement than with display."},
    5754: {"title": "Hallway", "desc": "The hallway keeps the temple's measured circular rhythm, guiding motion with a calm formality that feels practiced and old."},
    5755: {"title": "Hallway", "desc": "This stretch of hallway remains spare and disciplined, a ring of stone and quiet purpose within the broader temple interior."},
    5756: {"title": "Hallway", "desc": "The circular hallway feels slightly broader here, though the dominant impression is still one of ritual order, hush, and guided movement."},
    5772: {"title": "Hallway", "desc": "This farther segment of hallway carries the same contemplative ring-like flow, with the temple's geometry doing most of the speaking."},
    5773: {"title": "Hallway", "desc": "The hallway stays restrained and enclosed here, a place where movement seems expected to remain deliberate rather than hurried."},
    5774: {"title": "Hallway", "desc": "This temple passage keeps the same quiet rotational logic, its value lying in connection and ceremony rather than in decoration."},
    5775: {"title": "Hallway", "desc": "The hallway bends on through the temple with measured calm, holding together several internal routes without losing its solemn character."},
    5776: {"title": "Hallway", "desc": "This farther run of hallway remains austere and ordered, a contained interior path shaped by ritual use over long years."},
    5777: {"title": "Hallway", "desc": "Here the hallway still feels part of the same circular devotional circuit, quiet enough that even movement seems to lower its voice."},
    5778: {"title": "Hallway", "desc": "At this end of the ring, the hallway preserves the same calm architectural discipline, closing the circuit without fanfare."},
    5779: {"title": "Main Arch", "desc": "The main arch feels like a ceremonial hinge inside the temple, a threshold where enclosed hush gives way to something more focused beyond."},
    754: {"title": "Albreda Boulevard", "desc": "This end of Albreda Boulevard carries the same purposeful width as the rest, giving the road a slightly grander line without softening its practical use."},
    821: {"title": "Sicle Grove Lane", "desc": "Sicle Grove Lane keeps its enclosed neighborhood character here, a short urban lane whose importance lies in local connection rather than display."},
}

PHASE5_ROOM_SPECS = {
    899: {"title": "Esplanade Eluned", "desc": "Esplanade Eluned opens into a broader civic reach than the neighboring lanes, carrying a sense of promenade without ever escaping the Crossing's commercial gravity."},
    915: {"title": "Esplanade Eluned", "desc": "This stretch of Esplanade Eluned feels airy by local standards, though the stone, traffic, and nearby thresholds keep it firmly part of the working city."},
    916: {"title": "Esplanade Eluned", "desc": "Farther along, Esplanade Eluned balances open movement with urban wear, reading as a deliberate public road rather than a quiet retreat."},
    917: {"title": "Esplanade Eluned", "desc": "The esplanade keeps a steady civic rhythm here, broad enough for easy passage and busy enough to remind you the city never truly relaxes."},
    918: {"title": "Esplanade Eluned", "desc": "This middle stretch of Esplanade Eluned feels slightly more enclosed by adjoining fronts, but it still carries the district's wider, public-facing posture."},
    923: {"title": "Esplanade Eluned", "desc": "At this end the esplanade works like a major connector between neighboring squares and lanes, important because it gathers movement without fuss."},
    930: {"title": "Esplanade Eluned", "desc": "The far reach of Esplanade Eluned remains broad-backed and civic, a road that feels built for repeated public use rather than ornament."},
    826: {"title": "Riverpine Circle", "desc": "Riverpine Circle bends away from the straighter streets in a contained sweep of stone and frontage, giving the district a more residential cadence without leaving the city behind."},
    827: {"title": "Riverpine Circle", "desc": "This stretch of Riverpine Circle feels compact and settled, its curve organizing local traffic into a quieter rhythm than the nearby through-roads."},
    828: {"title": "Riverpine Circle", "desc": "The circle keeps a close, neighborhood character here, with repeated foot traffic and familiar turns mattering more than any public display."},
    829: {"title": "Riverpine Circle", "desc": "Farther along, Riverpine Circle remains contained and local, a curved seam of paving whose value lies in steady use and easy recognition."},
    830: {"title": "Riverpine Circle", "desc": "This middle reach of Riverpine Circle feels slightly more enclosed, with the curve and surrounding walls giving the place a sheltered urban tone."},
    831: {"title": "Riverpine Circle", "desc": "The circle narrows into a more intimate run here, though it still carries the same dependable neighborhood traffic that defines the rest of the loop."},
    832: {"title": "Riverpine Circle", "desc": "At the far end, Riverpine Circle closes out as a modest local road, more about tying the district together than drawing attention to itself."},
    16508: {"title": "Riverlace Lane", "desc": "Riverlace Lane threads through the district as a narrow, practiced route where the city feels close on both sides and every turn seems locally known."},
    16509: {"title": "Riverlace Lane", "desc": "This stretch of Riverlace Lane feels quick and workaday, a lane shaped by routine passage rather than by any attempt at civic drama."},
    16510: {"title": "Riverlace Lane", "desc": "Riverlace Lane keeps a compact neighborhood scale here, its worn paving and tight frontage suggesting long, ordinary use."},
    16511: {"title": "Riverlace Lane", "desc": "Farther in, the lane feels more enclosed and slightly quieter, though the Crossing's steady movement still presses through the space."},
    16512: {"title": "Riverlace Lane", "desc": "This middle reach of Riverlace Lane remains modest and direct, useful because it links nearby corners without pretending to be anything grander."},
    16513: {"title": "Riverlace Lane", "desc": "At its far end, Riverlace Lane still reads as a small local seam of the city, defined by familiarity, repetition, and tight urban geometry."},
    13586: {"title": "Immortals' Walk", "desc": "Immortals' Walk carries a more ceremonial tone than the trade-heavy streets nearby, though the Crossing's practical life still keeps the road grounded."},
    13587: {"title": "Immortals' Walk", "desc": "This stretch of Immortals' Walk feels deliberate and somewhat reverent, a public way whose dignity comes from use and memory rather than sheer scale."},
    13588: {"title": "Immortals' Walk", "desc": "Farther along, Immortals' Walk balances civic gravity with the ordinary motion of the city, never fully escaping the daily traffic around it."},
    13589: {"title": "Immortals' Walk", "desc": "The walk remains broad and composed here, a road that seems meant to carry both public passage and a measure of reflection."},
    13590: {"title": "Immortals' Walk", "desc": "This middle reach of Immortals' Walk feels more enclosed by surrounding stone, but it still keeps the district's ceremonial bearing intact."},
    13591: {"title": "Immortals' Walk", "desc": "At the approach end, Immortals' Walk works as a dignified hinge between the city proper and the more self-contained walk beyond."},
    948: {"title": "Mongers' Bazaar", "desc": "Mongers' Bazaar presses market life into a dense knot of voices, wares, and constant negotiation, busy in the deeply practical way only a true bazaar can be."},
    949: {"title": "Mongers' Bazaar", "desc": "This stretch of Mongers' Bazaar feels crowded even between transactions, with stall lines and human traffic competing for the same short breath of space."},
    950: {"title": "Mongers' Bazaar", "desc": "Farther in, the bazaar becomes a tighter storm of commerce, all motion, display, and quick judgment under persistent urban noise."},
    951: {"title": "Mongers' Bazaar", "desc": "The bazaar keeps its compressed, argumentative energy here, a market seam where every step seems to offer another distraction or another obstacle."},
    952: {"title": "Mongers' Bazaar", "desc": "This reach of Mongers' Bazaar feels especially crowded with trade momentum, a place where movement and transaction constantly interfere with one another."},
    953: {"title": "Mongers' Bazaar", "desc": "At its far side, Mongers' Bazaar remains loud, close, and unmistakably commercial, a market knot built around repeated bargaining and daily wear."},
    947: {"title": "Mongers' Square", "desc": "Mongers' Square serves as the bazaar's hinge to the wider district, a busy public knot where market traffic spills back into the surrounding streets."},
    739: {"title": "Immortals' Approach", "desc": "Immortals' Approach narrows the city's ordinary traffic into a more directed civic run, clearly leading toward something more deliberate beyond."},
    741: {"title": "Immortals' Approach", "desc": "This farther stretch of Immortals' Approach keeps the same transitional dignity, bridging everyday Crossing movement into the quieter gravity of the walk ahead."},
}

PHASE6_ROOM_SPECS = {
    735: {"title": "Asemath Walk", "desc": "This branch of Asemath Walk feels more local than the busier stretches near the Green, a short stone run that still carries the Academy-side traffic of people with specific destinations."},
    736: {"title": "Water Street", "desc": "Water Street narrows into a damp, river-marked service lane where the city feels close on both sides and most movement seems tied to work rather than leisure."},
    737: {"title": "Water Street", "desc": "Farther along, Water Street keeps the same practical dockward mood, with worn paving and cramped frontage suggesting a road used more than admired."},
    738: {"title": "Full Moons Crescent", "desc": "Full Moons Crescent bends away from the straighter trade roads in a quieter civic curve, though the surrounding city still keeps the place tied to ordinary movement and errands."},
    740: {"title": "Werfnen's Strole", "desc": "Werfnen's Strole feels like a short, self-contained side street, the kind of tucked-away lane whose importance comes from the few doors and turnoffs it serves directly."},
    742: {"title": "Gull's View Lane", "desc": "Gull's View Lane carries a faint riverward openness without losing its urban footing, a narrow lane where the air moves a little more freely than the surrounding streets."},
    743: {"title": "Gull's View Lane", "desc": "This farther stretch of Gull's View Lane feels slightly more exposed and transitional, linking the inner lane to the terrace beyond without becoming grand about it."},
    755: {"title": "Albreda Alley", "desc": "Albreda Alley is a compact service cut off the broader boulevard, tight enough to feel private but busy enough to prove it matters to the block around it."},
    775: {"title": "Trollferry Approach", "desc": "This end of Trollferry Approach gathers several local routes into one practical junction, more shaped by people heading somewhere necessary than by any wish to linger."},
    777: {"title": "Embankment", "desc": "The embankment runs in a narrow river-edge line of worn stone and retaining work, a place that feels built to hold its ground as much as to carry traffic."},
    778: {"title": "Embankment", "desc": "Farther along, the embankment keeps the same exposed, hard-used character, with water, stone, and the pressure of the river never far from mind."},
    781: {"title": "S'zella Plaza", "desc": "S'zella Plaza opens just enough to register as a public pause in the street grid, though its real character still comes from constant passage and nearby business."},
    797: {"title": "Boar Alley", "desc": "Boar Alley is a narrow, workmanlike passage where doors and side trade matter more than any pretense of civic display, giving the whole cut a brisk, local energy."},
    809: {"title": "Covered Alleyway", "desc": "The covered alleyway feels compressed and shadowed even in daylight, a short connector whose closeness and side doors make it more functional than inviting."},
    818: {"title": "Northeast Customs", "desc": "Northeast Customs has the constrained, supervised feel of a checkpoint embedded in the city, where gates, trail edges, and official traffic meet without ever becoming comfortable."},
    842: {"title": "Crofton Close", "desc": "Crofton Close is a modest enclosed lane where the paving, corners, and nearby walls all suggest familiar use rather than through-traffic on any larger civic scale."},
    866: {"title": "Western Gate", "desc": "The western gate stands as a sturdier threshold than the smaller lanes around it, with gate traffic, stair access, and adjoining routes giving the place a deliberate edge-of-city weight."},
    886: {"title": "Ustial Road", "desc": "Ustial Road carries a quieter, more guarded tone than the brighter streets nearby, a road whose connected side buildings make it feel useful in ways it does not advertise."},
    887: {"title": "Scorpion Lane", "desc": "Scorpion Lane is tight, direct, and a little sharper in mood than the surrounding blocks, the sort of street that looks as though it rewards already knowing why you came."},
    894: {"title": "Scorpion Lane", "desc": "Farther along, Scorpion Lane becomes a more active knot of side traffic and adjoining doors, holding together several nearby seams of the district at once."},
    895: {"title": "Commerce Avenue", "desc": "Commerce Avenue feels unapologetically mercantile, a clean practical run of road where guild traffic, supply movement, and everyday negotiation all pass in plain view."},
    896: {"title": "Commerce Avenue", "desc": "This farther reach of Commerce Avenue carries the same brisk trade-facing energy, linking adjoining streets and guildward traffic without losing its orderly commercial bearing."},
    897: {"title": "Ustial Road", "desc": "This stretch of Ustial Road works like a hinge between quieter lanes and more specialized interiors, its crossings and turnoffs giving it a watchful, transitional character."},
    898: {"title": "Stevedore's Wend", "desc": "Stevedore's Wend curls through the dockside blocks in a short, labor-marked bend of paving where old warehouse traffic still seems to hang in the air."},
    900: {"title": "Mercantile Street", "desc": "Mercantile Street presents commerce directly and without apology, a road of thresholds, work, and transaction where everything looks arranged to keep goods and people moving."},
    902: {"title": "Water Sprite Way", "desc": "This branch of Water Sprite Way keeps one foot in the river district and one in the city proper, carrying damp air and quick side traffic through a narrow urban seam."},
    914: {"title": "Scullion Way", "desc": "Scullion Way is a compact service road whose name suits it, a narrow stretch that feels defined by errands, deliveries, and the practical movement behind larger public streets."},
    921: {"title": "Haven's End", "desc": "Haven's End sits at the edge of busier routes with a slightly more sheltered mood, though the tavern traffic and adjoining paths keep it firmly in the city's routine."},
    922: {"title": "Haven's End", "desc": "Farther along, Haven's End feels more like the quiet edge of a district than a destination in itself, a short run of road balanced between riverbank access and nearby city traffic."},
    928: {"title": "Chieftain Walk", "desc": "Chieftain Walk serves as a purposeful connector between heavier civic routes, broad enough to gather movement from several directions without turning into a true square."},
    929: {"title": "Chieftain Walk", "desc": "This farther stretch of Chieftain Walk feels more workmanlike than ceremonial, a road meant to hand traffic onward rather than claim attention for itself."},
    957: {"title": "Alfren's Ferry", "desc": "Alfren's Ferry is less a street than a river-edge threshold, a travel point where squareward traffic yields to transport, waiting, and the practical machinery of crossing water."},
    8235: {"title": "Werfnen's Strole", "desc": "This isolated pocket of Werfnen's Strole feels like the end of a small internal spur, a quiet corner whose enclosure makes it read more like a tucked-away landing than a through street."},
}


def load_canonical_crossing_map(map_path=DEFAULT_MAP_PATH):
    path = Path(map_path)
    if not path.exists():
        raise FileNotFoundError(f"Canonical Crossing map JSON not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Canonical Crossing map JSON must be a top-level list.")
    sample = next((room for room in data if _canonical_crossing_title(room)), None)
    if sample is None:
        raise ValueError("Canonical Crossing map JSON does not contain any The Crossing room titles.")
    required = {"id", "title", "description", "paths", "wayto", "timeto", "image", "image_coords", "tags"}
    missing = sorted(required.difference(sample))
    if missing:
        raise ValueError(f"Canonical Crossing room entries are missing required keys: {missing}")
    return data


def _canonical_crossing_title(room):
    for raw in room.get("title", []) or []:
        text = str(raw or "").strip()
        match = re.match(r"^\[\[(The Crossing(?: [^,\]]+)?)\s*,\s*(.+?)\]\]$", text)
        if match and match.group(1).startswith("The Crossing"):
            return match.group(2).strip()
    return None


def extract_crossing_entries(data):
    entries = {}
    for room in data:
        title = _canonical_crossing_title(room)
        if not title:
            continue
        entries[int(room["id"])] = {
            "id": int(room["id"]),
            "canonical_title": title,
            "description": list(room.get("description", []) or []),
            "paths": list(room.get("paths", []) or []),
            "wayto": dict(room.get("wayto", {}) or {}),
            "timeto": dict(room.get("timeto", {}) or {}),
            "tags": list(room.get("tags", []) or []),
            "image": str(room.get("image") or ""),
            "image_coords": list(room.get("image_coords", []) or []),
        }
    return entries


def phase1_entries_from_map(data, room_ids=None):
    entries = extract_crossing_entries(data)
    selected = {}
    missing = []
    for room_id in room_ids or PHASE1_ROOM_IDS:
        entry = entries.get(int(room_id))
        if entry is None:
            missing.append(int(room_id))
            continue
        expected_title = PHASE1_ROOM_SPECS[int(room_id)]["title"]
        if entry["canonical_title"] != expected_title:
            raise ValueError(
                f"Canonical room id {room_id} resolved to {entry['canonical_title']!r}, expected {expected_title!r}."
            )
        selected[int(room_id)] = entry
    if missing:
        raise ValueError(f"Canonical Crossing phase 1 room ids missing from map JSON: {missing}")
    return selected


def _find_room_by_map_id(canonical_map_id):
    for room in ObjectDB.objects.get_by_tag(str(int(canonical_map_id)), category=CANONICAL_ID_CATEGORY):
        if getattr(room, "db_typeclass_path", "") == ROOM_TYPECLASS:
            return room
    return None


def _find_exit(source, key, aliases=None):
    wanted = {str(key or "").strip().lower()}
    wanted.update(str(alias or "").strip().lower() for alias in aliases or [])
    for obj in list(getattr(source, "contents", []) or []):
        if getattr(obj, "db_typeclass_path", "") != EXIT_TYPECLASS:
            continue
        names = {str(getattr(obj, "key", "") or "").strip().lower()}
        names.update(str(alias or "").strip().lower() for alias in getattr(getattr(obj, "aliases", None), "all", lambda: [])())
        if names.intersection(wanted):
            return obj
    return None


def _normalize_exit_command(command):
    text = str(command or "").strip()
    if not text:
        return None, []
    if text in DIR_ALIASES:
        return text, list(DIR_ALIASES[text])
    for prefix in ("go ", "climb ", "enter "):
        if text.startswith(prefix):
            return text[len(prefix):].strip(), [text]
    return text, []


def _ensure_room(entry):
    spec = PHASE1_ROOM_SPECS[int(entry["id"])]
    return _ensure_room_with_spec(entry, spec, canonical_phase=1, area_tag=CANONICAL_AREA_TAG)


def _ensure_room_with_spec(entry, spec, *, canonical_phase, area_tag):
    room = _find_room_by_map_id(entry["id"])
    if room is None:
        room = create_object(ROOM_TYPECLASS, key=spec["title"], nohome=True)
    room.key = spec["title"]
    room.db.desc = spec["desc"]
    room.db.area = AREA_NAME
    room.db.region_name = AREA_NAME
    room.db.canonical_map_id = int(entry["id"])
    room.db.canonical_title = entry["canonical_title"]
    room.db.canonical_paths = str((entry.get("paths") or [""])[0] or "")
    room.db.canonical_tags = list(entry.get("tags") or [])
    room.db.canonical_timeto = dict(entry.get("timeto") or {})
    room.db.canonical_image = str(entry.get("image") or "")
    room.db.canonical_image_coords = list(entry.get("image_coords") or [])
    room.db.is_canonical_crossing = True
    room.db.canonical_phase = int(canonical_phase)
    room.db.canonical_source = "direlore:map-1777858104.json"
    room.tags.add(area_tag)
    room.tags.add(str(int(entry["id"])), category=CANONICAL_ID_CATEGORY)
    room.aliases.add(str(entry["canonical_title"] or "").lower())
    return room


def phase2_entries_from_map(data, room_ids=None):
    entries = extract_crossing_entries(data)
    selected = {}
    missing = []
    for room_id in room_ids or PHASE2_ROOM_IDS:
        entry = entries.get(int(room_id))
        if entry is None:
            missing.append(int(room_id))
            continue
        expected_title = PHASE2_ROOM_SPECS[int(room_id)]["title"]
        if entry["canonical_title"] != expected_title:
            raise ValueError(
                f"Canonical room id {room_id} resolved to {entry['canonical_title']!r}, expected {expected_title!r}."
            )
        selected[int(room_id)] = entry
    if missing:
        raise ValueError(f"Canonical Crossing phase 2 room ids missing from map JSON: {missing}")
    return selected


def phase3_entries_from_map(data, room_ids=None):
    entries = extract_crossing_entries(data)
    selected = {}
    missing = []
    for room_id in room_ids or PHASE3_ROOM_IDS:
        entry = entries.get(int(room_id))
        if entry is None:
            missing.append(int(room_id))
            continue
        expected_title = PHASE3_ROOM_SPECS[int(room_id)]["title"]
        if entry["canonical_title"] != expected_title:
            raise ValueError(
                f"Canonical room id {room_id} resolved to {entry['canonical_title']!r}, expected {expected_title!r}."
            )
        selected[int(room_id)] = entry
    if missing:
        raise ValueError(f"Canonical Crossing phase 3 room ids missing from map JSON: {missing}")
    return selected


def phase4_entries_from_map(data, room_ids=None):
    entries = extract_crossing_entries(data)
    selected = {}
    missing = []
    for room_id in room_ids or PHASE4_ROOM_IDS:
        entry = entries.get(int(room_id))
        if entry is None:
            missing.append(int(room_id))
            continue
        expected_title = PHASE4_ROOM_SPECS[int(room_id)]["title"]
        if entry["canonical_title"] != expected_title:
            raise ValueError(
                f"Canonical room id {room_id} resolved to {entry['canonical_title']!r}, expected {expected_title!r}."
            )
        selected[int(room_id)] = entry
    if missing:
        raise ValueError(f"Canonical Crossing phase 4 room ids missing from map JSON: {missing}")
    return selected


def phase5_entries_from_map(data, room_ids=None):
    entries = extract_crossing_entries(data)
    selected = {}
    missing = []
    for room_id in room_ids or PHASE5_ROOM_IDS:
        entry = entries.get(int(room_id))
        if entry is None:
            missing.append(int(room_id))
            continue
        expected_title = PHASE5_ROOM_SPECS[int(room_id)]["title"]
        if entry["canonical_title"] != expected_title:
            raise ValueError(
                f"Canonical room id {room_id} resolved to {entry['canonical_title']!r}, expected {expected_title!r}."
            )
        selected[int(room_id)] = entry
    if missing:
        raise ValueError(f"Canonical Crossing phase 5 room ids missing from map JSON: {missing}")
    return selected


def phase6_entries_from_map(data, room_ids=None):
    entries = extract_crossing_entries(data)
    selected = {}
    missing = []
    for room_id in room_ids or PHASE6_ROOM_IDS:
        entry = entries.get(int(room_id))
        if entry is None:
            missing.append(int(room_id))
            continue
        expected_title = PHASE6_ROOM_SPECS[int(room_id)]["title"]
        if entry["canonical_title"] != expected_title:
            raise ValueError(
                f"Canonical room id {room_id} resolved to {entry['canonical_title']!r}, expected {expected_title!r}."
            )
        selected[int(room_id)] = entry
    if missing:
        raise ValueError(f"Canonical Crossing phase 6 room ids missing from map JSON: {missing}")
    return selected


def _collect_imported_rooms(room_ids):
    rooms = {}
    for room_id in room_ids:
        room = _find_room_by_map_id(room_id)
        if room is not None:
            rooms[int(room_id)] = room
    return rooms


def _populate_room_pending_exits(room, entry, imported_rooms):
    pending = []
    for destination_id, command in dict(entry.get("wayto") or {}).items():
        try:
            destination_id = int(destination_id)
        except (TypeError, ValueError):
            continue
        destination = imported_rooms.get(destination_id)
        if destination is None:
            pending.append({"destination_id": destination_id, "command": str(command or "")})
            continue
        _ensure_exit(room, destination, command)
    room.db.pending_canonical_exits = pending


def _drain_pending_exits(rooms, imported_rooms):
    for room in rooms.values():
        pending = []
        for entry in list(getattr(room.db, "pending_canonical_exits", []) or []):
            try:
                destination_id = int(entry.get("destination_id"))
            except (TypeError, ValueError, AttributeError):
                continue
            destination = imported_rooms.get(destination_id)
            if destination is None:
                pending.append({"destination_id": destination_id, "command": str(entry.get("command") or "")})
                continue
            _ensure_exit(room, destination, entry.get("command"))
        room.db.pending_canonical_exits = pending


def _ensure_exit(source, destination, command):
    key, aliases = _normalize_exit_command(command)
    if not key:
        return None
    exit_obj = _find_exit(source, key, aliases=aliases)
    if exit_obj is None:
        exit_obj = create_object(EXIT_TYPECLASS, key=key, location=source, destination=destination, nohome=True)
    exit_obj.key = key
    exit_obj.destination = destination
    for alias in aliases:
        exit_obj.aliases.add(alias)
    exit_obj.db.canonical_command = str(command or "")
    return exit_obj


def mark_new_landing_deprecated():
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        if str(getattr(getattr(room, "db", None), "area", None) or "").strip() != NEW_LANDING_AREA_NAME:
            continue
        room.db.deprecated_area = True
        room.db.deprecated_successor = AREA_NAME
        room.db.deprecation_note = DEPRECATION_NOTE


def ensure_canonical_crossing_phase1(map_path=DEFAULT_MAP_PATH, room_ids=None):
    data = load_canonical_crossing_map(map_path=map_path)
    entries = phase1_entries_from_map(data, room_ids=room_ids)
    rooms = {room_id: _ensure_room(entry) for room_id, entry in entries.items()}
    for room_id, entry in entries.items():
        pending = []
        for destination_id, command in dict(entry.get("wayto") or {}).items():
            try:
                destination_id = int(destination_id)
            except (TypeError, ValueError):
                continue
            destination = rooms.get(destination_id)
            if destination is None:
                pending.append({"destination_id": destination_id, "command": str(command or "")})
                continue
            _ensure_exit(rooms[room_id], destination, command)
        rooms[room_id].db.pending_canonical_exits = pending
    mark_new_landing_deprecated()
    return rooms


def ensure_canonical_crossing_phase2(map_path=DEFAULT_MAP_PATH, room_ids=None):
    data = load_canonical_crossing_map(map_path=map_path)
    phase2_ids = [int(room_id) for room_id in (room_ids or PHASE2_ROOM_IDS)]
    entries = phase2_entries_from_map(data, room_ids=phase2_ids)
    rooms = {
        room_id: _ensure_room_with_spec(entry, PHASE2_ROOM_SPECS[room_id], canonical_phase=2, area_tag=CANONICAL_AREA_TAG_PHASE2)
        for room_id, entry in entries.items()
    }
    imported_rooms = _collect_imported_rooms(PHASE1_ROOM_IDS + phase2_ids)
    for room_id, entry in entries.items():
        _populate_room_pending_exits(rooms[room_id], entry, imported_rooms)
    _drain_pending_exits(_collect_imported_rooms(PHASE1_ROOM_IDS), imported_rooms)
    mark_new_landing_deprecated()
    return rooms


def ensure_canonical_crossing_phase3(map_path=DEFAULT_MAP_PATH, room_ids=None):
    data = load_canonical_crossing_map(map_path=map_path)
    phase3_ids = [int(room_id) for room_id in (room_ids or PHASE3_ROOM_IDS)]
    entries = phase3_entries_from_map(data, room_ids=phase3_ids)
    rooms = {
        room_id: _ensure_room_with_spec(entry, PHASE3_ROOM_SPECS[room_id], canonical_phase=3, area_tag=CANONICAL_AREA_TAG_PHASE3)
        for room_id, entry in entries.items()
    }
    imported_rooms = _collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + phase3_ids)
    for room_id, entry in entries.items():
        _populate_room_pending_exits(rooms[room_id], entry, imported_rooms)
    _drain_pending_exits(_collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS), imported_rooms)
    mark_new_landing_deprecated()
    return rooms


def ensure_canonical_crossing_phase4(map_path=DEFAULT_MAP_PATH, room_ids=None):
    data = load_canonical_crossing_map(map_path=map_path)
    phase4_ids = [int(room_id) for room_id in (room_ids or PHASE4_ROOM_IDS)]
    entries = phase4_entries_from_map(data, room_ids=phase4_ids)
    rooms = {
        room_id: _ensure_room_with_spec(entry, PHASE4_ROOM_SPECS[room_id], canonical_phase=4, area_tag=CANONICAL_AREA_TAG_PHASE4)
        for room_id, entry in entries.items()
    }
    imported_rooms = _collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS + phase4_ids)
    for room_id, entry in entries.items():
        _populate_room_pending_exits(rooms[room_id], entry, imported_rooms)
    _drain_pending_exits(_collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS), imported_rooms)
    mark_new_landing_deprecated()
    return rooms


def ensure_canonical_crossing_phase5(map_path=DEFAULT_MAP_PATH, room_ids=None):
    data = load_canonical_crossing_map(map_path=map_path)
    phase5_ids = [int(room_id) for room_id in (room_ids or PHASE5_ROOM_IDS)]
    entries = phase5_entries_from_map(data, room_ids=phase5_ids)
    rooms = {
        room_id: _ensure_room_with_spec(entry, PHASE5_ROOM_SPECS[room_id], canonical_phase=5, area_tag=CANONICAL_AREA_TAG_PHASE5)
        for room_id, entry in entries.items()
    }
    imported_rooms = _collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS + PHASE4_ROOM_IDS + phase5_ids)
    for room_id, entry in entries.items():
        _populate_room_pending_exits(rooms[room_id], entry, imported_rooms)
    _drain_pending_exits(_collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS + PHASE4_ROOM_IDS), imported_rooms)
    mark_new_landing_deprecated()
    return rooms


def ensure_canonical_crossing_phase6(map_path=DEFAULT_MAP_PATH, room_ids=None):
    from .guildhall_stubs import GUILDHALL_STUB_ROOM_IDS

    data = load_canonical_crossing_map(map_path=map_path)
    phase6_ids = [int(room_id) for room_id in (room_ids or PHASE6_ROOM_IDS)]
    entries = phase6_entries_from_map(data, room_ids=phase6_ids)
    rooms = {
        room_id: _ensure_room_with_spec(entry, PHASE6_ROOM_SPECS[room_id], canonical_phase=6, area_tag=CANONICAL_AREA_TAG_PHASE6)
        for room_id, entry in entries.items()
    }
    imported_rooms = _collect_imported_rooms(
        PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS + PHASE4_ROOM_IDS + PHASE5_ROOM_IDS + phase6_ids + GUILDHALL_STUB_ROOM_IDS
    )
    for room_id, entry in entries.items():
        _populate_room_pending_exits(rooms[room_id], entry, imported_rooms)
    _drain_pending_exits(
        _collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS + PHASE4_ROOM_IDS + PHASE5_ROOM_IDS + GUILDHALL_STUB_ROOM_IDS),
        imported_rooms,
    )
    mark_new_landing_deprecated()
    return rooms


def get_canonical_crossing_arrival_room():
    room = _find_room_by_map_id(ARRIVAL_ROOM_ID)
    if room and bool(getattr(getattr(room, "db", None), "is_canonical_crossing", False)):
        return room
    return None


def ensure_canonical_guildhall_stubs(map_path=DEFAULT_MAP_PATH, room_ids=None):
    from .guildhall_stubs import ensure_canonical_guildhall_stubs as _ensure_canonical_guildhall_stubs

    return _ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=room_ids)