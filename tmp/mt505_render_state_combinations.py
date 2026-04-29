from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = REPO_ROOT / "exports" / "mt505_claude_capability.txt"
OUTPUT_PATH = REPO_ROOT / "exports" / "mt505_state_renders.md"
FRAGMENT_RE = re.compile(r"\$state\(([^,]+),(.*?)\)", re.DOTALL)


def _parse_blocks(text: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for raw_block in text.split("\n## ")[1:]:
        heading, remainder = raw_block.split("\n\n", 1)
        if " — " not in heading:
            continue
        room_id, name = heading.split(" — ", 1)
        env_match = re.search(r"Environment: (.*?)\n", remainder)
        groups_match = re.search(r"Applicable groups: (.*?)\n", remainder)
        states_match = re.search(r"Applicable states: (.*?)\n\n", remainder)
        pass_1_match = re.search(r"### Pass 1 \(plain prose\):\n(.*?)\n\n### Pass 2", remainder, re.DOTALL)
        pass_2_match = re.search(r"### Pass 2 \(with markup\):\n(.*?)(?:\n\n-+|\n\n## Run Summary|\Z)", remainder, re.DOTALL)
        blocks.append(
            {
                "room_id": room_id.strip(),
                "name": name.strip(),
                "environment": env_match.group(1).strip() if env_match else "",
                "groups": groups_match.group(1).strip() if groups_match else "",
                "states": states_match.group(1).strip() if states_match else "",
                "pass_1": pass_1_match.group(1).strip() if pass_1_match else "",
                "pass_2": pass_2_match.group(1).strip() if pass_2_match else "",
            }
        )
    return blocks


def _render(markup: str, active_states: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        content = match.group(2)
        return content if name in active_states else ""

    rendered = FRAGMENT_RE.sub(replace, markup)
    rendered = re.sub(r"[ \t]{2,}", " ", rendered)
    rendered = re.sub(r"\s+([,.;:])", r"\1", rendered)
    rendered = re.sub(r"\(\s+", "(", rendered)
    rendered = re.sub(r"\s+\)", ")", rendered)
    return rendered.strip()


def main() -> int:
    source = INPUT_PATH.read_text(encoding="utf-8")
    rooms = _parse_blocks(source)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        handle.write("# MT-505 State Combination Renders\n\n")

        for room in rooms:
            groups = {item.strip() for item in room["groups"].split(",") if item.strip()}
            markup = room["pass_2"]
            handle.write(f"## {room['room_id']} — {room['name']}\n\n")
            handle.write(f"Environment: {room['environment']}\n\n")

            if markup.startswith("[ERROR:"):
                handle.write("### Raw markup\n\n")
                handle.write(f"```text\n{markup}\n```\n\n")
                handle.write("### Renders\n\n")
                handle.write("Pass 2 failed; no renders generated.\n\n")
                continue

            combos: list[tuple[str, set[str]]] = [
                ("default", set()),
                ("morning_clear", {"morning"}),
                ("midday_clear", {"midday"}),
                ("evening_clear", {"evening"}),
                ("night_clear", {"night"}),
            ]
            if "weather" in groups:
                combos.append(("morning_rain", {"morning", "rain"}))
                combos.append(("evening_snow", {"evening", "snow"}))
            if "invasion" in groups:
                combos.append(("night_invasion", {"night", "invasion"}))
            combos.extend(
                [
                    ("winter_morning", {"winter", "morning"}),
                    ("summer_midday", {"summer", "midday"}),
                ]
            )

            handle.write("### Raw markup\n\n")
            handle.write(f"```text\n{markup}\n```\n\n")

            for label, active in combos:
                handle.write(f"### {label}\n\n")
                handle.write(f"```text\n{_render(markup, active)}\n```\n\n")

    print(f"Output saved to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())