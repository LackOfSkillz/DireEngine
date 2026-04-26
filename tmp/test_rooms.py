from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from world.area_forge.extract.cv_pipeline import detect_rooms, draw_rooms, load_bgr


def main() -> int:
    map_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("maps/CrossingMap (1).png")
    print(cv2.__version__)
    img = load_bgr(str(map_path))
    rooms = detect_rooms(img)
    print(len(rooms))
    print(Counter(room["color"] for room in rooms))
    cv2.imwrite("debug_rooms.png", draw_rooms(img, rooms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())