from __future__ import annotations

import os
import sys
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from tools.generate_sample_descriptions import load_generation_zone, setup_django  # noqa: E402
from world.builder.prompting.room_description_prompt import (  # noqa: E402
    determine_applicable_state_groups,
    determine_applicable_states,
)


try:
    import anthropic
except ImportError as exc:  # pragma: no cover - exercised by runtime environment
    raise SystemExit("Anthropic SDK not installed. Run: pip install anthropic") from exc


MARKUP_SYSTEM_PROMPT = """You add Evennia $state(...) markup to existing MUD room descriptions.

Your input is an existing description plus a list of applicable world states.

Your job: identify atmospheric or sensory phrases in the description and wrap them in $state(name, content) syntax so the description can render differently based on world state.

Syntax: $state(name, content) where name is one of the applicable states and content is text that grammatically extends the surrounding sentence.

CRITICAL RULES:
1. The base prose MUST remain grammatically valid when ALL fragments are removed.
2. The base prose MUST remain grammatically valid when ANY combination of fragments is active.
3. Wrap atmospheric beats only: light quality, weather effects on visible surfaces, ambient sound, seasonal atmosphere, special events.
4. NEVER wrap permanent features: exits, layout, building positions, road shapes.
5. For each applicable state group, add at least one fragment if a natural beat exists.
6. Whitespace: leading/trailing spaces go INSIDE the fragment so removal doesn't leave double spaces.
7. Mutually exclusive states (morning/midday/evening/night) can have multiple fragments at the same insertion point - only one will fire at any time.

EXAMPLE:

Input description: "Stone Lane ends here against close-packed buildings, its narrow cobbles worn smooth by constant traffic. Light spreads across the lane. Underfoot, the stones are dark with use."
Applicable states: spring, summer, autumn, winter, morning, midday, evening, night, rain, snow, fog
Applicable state groups: season, time, weather

Output:
Stone Lane ends here against close-packed buildings, its narrow cobbles worn smooth by constant traffic. Light$state(morning, spreads gold from the east)$state(midday, falls bright across the cobbles)$state(evening, fades behind the rooftops)$state(night, is absent except for distant lantern-glow). Underfoot, the stones are dark with use$state(rain, and slick with rainwater)$state(snow, beneath a fresh white covering)$state(winter, with patches of frost in the shadowed corners).

Return ONLY the description with markup added. No commentary, no labels, no other text."""

ROOM_TARGETS = [
    ("crossingV2", "crossingV2_192_132"),
    ("crossingV2", "crossingV2_178_132"),
    ("demo1", "CRO_500_100"),
]
PASS_1_OUTPUTS = {
    "crossingV2_192_132": (
        "The narrow lane ends abruptly here against a high stone wall to the "
        "east, with its sole exit leading west toward the bustling heart of "
        "the city. Cobblestones underfoot are well-worn from constant traffic, "
        "darkened and slick in spots where vendors once set up their stalls. "
        "The air carries faint traces of river water mixed with distant market "
        "clamor."
    ),
    "crossingV2_178_132": (
        "A narrow hallway in a bustling tavern runs east and south, its "
        "earthen floor showing signs of wear from steady traffic. A hearth at "
        "the center casts flickering light over the worn surfaces. Outside, "
        "the sounds of river trade mix with the murmur of conversation within "
        "the hall."
    ),
    "CRO_500_100": (
        "A narrow passage runs west and descends to the south through rough "
        "earthen walls. The floor is uneven, marked by occasional footprints "
        "that suggest sporadic use. The air carries a faint hint of moisture "
        "from beyond the passage's boundaries."
    ),
}
OUTPUT_PATH = REPO_ROOT / "exports" / "mt503_qwen_vs_claude_markup.txt"


def build_markup_user_message(description: str, states: list[str], groups: list[str]) -> str:
    return (
        f"Description:\n{description}\n\n"
        f"Applicable states: {', '.join(states)}\n"
        f"Applicable state groups: {', '.join(groups)}\n\n"
        "Add $state(...) markup. Each applicable state group needs at least "
        "one fragment if a natural atmospheric beat exists in the description."
    )


def call_qwen_markup(description: str, states: list[str], groups: list[str]) -> str:
    user_message = build_markup_user_message(description, states, groups)
    response = requests.post(
        os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234") + "/v1/chat/completions",
        json={
            "model": os.getenv("LLM_MODEL", "qwen2.5-14b-instruct"),
            "messages": [{"role": "user", "content": f"{MARKUP_SYSTEM_PROMPT}\n\n{user_message}"}],
            "temperature": 0.3,
            "max_tokens": 400,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def call_claude_markup(description: str, states: list[str], groups: list[str]) -> str:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        system=MARKUP_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": build_markup_user_message(description, states, groups),
            }
        ],
    )
    return response.content[0].text.strip()


def main() -> int:
    setup_django()
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        handle.write("MT-503 - Qwen vs Claude markup comparison\n")
        handle.write("=" * 60 + "\n\n")

        for zone_id, room_id in ROOM_TARGETS:
            zone = load_generation_zone(zone_id)
            room_index = {str(room.get("id") or "").strip(): room for room in zone.get("rooms") or []}
            room = room_index[room_id]
            groups = determine_applicable_state_groups(room, zone)
            states = determine_applicable_states(room, zone)
            base = PASS_1_OUTPUTS[room_id]

            handle.write(f"## {room_id}\n\n")
            handle.write(f"Applicable groups: {', '.join(groups)}\n")
            handle.write(f"Applicable states: {', '.join(states)}\n\n")
            handle.write(f"### Pass 1 (Qwen prose, baseline):\n{base}\n\n")

            print(f"[{room_id}] Calling Qwen for markup...")
            try:
                qwen_output = call_qwen_markup(base, states, groups)
                handle.write(f"### Pass 2a (Qwen markup):\n{qwen_output}\n\n")
            except Exception as exc:  # pragma: no cover - runtime integration path
                handle.write(f"### Pass 2a (Qwen markup):\n[ERROR: {exc}]\n\n")

            print(f"[{room_id}] Calling Claude for markup...")
            try:
                claude_output = call_claude_markup(base, states, groups)
                handle.write(f"### Pass 2b (Claude markup):\n{claude_output}\n\n")
            except Exception as exc:  # pragma: no cover - runtime integration path
                handle.write(f"### Pass 2b (Claude markup):\n[ERROR: {exc}]\n\n")

            handle.write("-" * 60 + "\n\n")
            print(f"[{room_id}] Done.\n")

    print(f"Output saved to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())