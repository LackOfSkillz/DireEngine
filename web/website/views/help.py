import ast
import re
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from evennia.utils import logger
from evennia.utils.ansi import strip_ansi
from evennia.help.filehelp import FILE_HELP_ENTRIES


PUBLIC_HIDDEN_CATEGORIES = {"admin", "builder"}

BASE_DIR = Path(__file__).resolve().parents[3]
COMMANDS_DIR = BASE_DIR / "commands"
CMD_HELP_PATH = COMMANDS_DIR / "cmd_help.py"

CATEGORY_LABELS = {
    "communication": "Communication",
    "character": "Character",
    "general": "General",
    "combat": "Combat",
    "stealth": "Stealth",
    "survival": "Survival",
    "lore": "Lore",
    "training & lore": "Training & Lore",
    "magic": "Magic",
    "justice": "Justice",
    "system": "System",
    "builder": "Builder",
    "admin": "Admin",
}

CATEGORY_ORDER = {
    "communication": 10,
    "character": 20,
    "general": 30,
    "combat": 40,
    "stealth": 50,
    "survival": 60,
    "lore": 70,
    "training & lore": 80,
    "magic": 90,
    "justice": 100,
    "system": 110,
    "builder": 120,
    "admin": 130,
}

SECTION_LABELS = OrderedDict(
    (
        ("commands", "Commands"),
        ("guides", "Guides & Reference"),
    )
)

USAGE_LINE_RE = re.compile(r"^usage:\s*(.*)$", re.IGNORECASE)
SECTION_LINE_RE = re.compile(r"^[A-Z][A-Za-z\s/&-]+:$")


def normalize_category(raw_category):
    category = (raw_category or "General").strip().lower()
    return category or "general"


def display_category(raw_category):
    normalized = normalize_category(raw_category)
    return CATEGORY_LABELS.get(normalized, raw_category.strip().title() if raw_category else "General")


def category_sort_key(raw_category):
    normalized = normalize_category(raw_category)
    return (CATEGORY_ORDER.get(normalized, 999), display_category(raw_category).lower())


def clean_help_text(text):
    return strip_ansi((text or "").replace("\r\n", "\n")).strip()


def extract_usage(text, default_usage):
    lines = clean_help_text(text).split("\n")

    for index, line in enumerate(lines):
        match = USAGE_LINE_RE.match(line.strip())
        if not match:
            continue

        usage_lines = []
        inline_usage = match.group(1).strip()
        if inline_usage:
            usage_lines.append(inline_usage)

        cursor = index + 1
        while cursor < len(lines):
            candidate = lines[cursor].strip()
            if not candidate:
                if usage_lines:
                    break
                cursor += 1
                continue
            if SECTION_LINE_RE.match(candidate):
                break
            usage_lines.append(candidate)
            cursor += 1

        if usage_lines:
            return " ".join(usage_lines)

    in_examples = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower() == "examples:":
            in_examples = True
            continue
        if in_examples:
            if SECTION_LINE_RE.match(stripped):
                break
            return stripped

    return default_usage


def extract_summary(text):
    lines = clean_help_text(text).split("\n")
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if summary_lines:
                break
            continue
        if stripped.lower() in {"usage:", "examples:"}:
            break
        if USAGE_LINE_RE.match(stripped) or SECTION_LINE_RE.match(stripped):
            break
        summary_lines.append(stripped)

    return " ".join(summary_lines)


def parse_aliases(value):
    if isinstance(value, str):
        return [part.strip().lower() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(part).strip().lower() for part in value if str(part).strip()]
    return []


def safe_literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [safe_literal(item) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(safe_literal(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return {safe_literal(key): safe_literal(value) for key, value in zip(node.keys, node.values)}
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "OrderedDict" and node.args:
        return OrderedDict(safe_literal(node.args[0]))
    raise ValueError(f"Unsupported literal node: {ast.dump(node, include_attributes=False)}")


@lru_cache(maxsize=1)
def load_command_catalog():
    catalog = {}

    for command_path in COMMANDS_DIR.glob("cmd_*.py"):
        tree = ast.parse(command_path.read_text(encoding="utf-8-sig"), filename=str(command_path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue

            metadata = {
                "name": None,
                "aliases": [],
                "auto_help": True,
                "help_category": "general",
                "doc": ast.get_docstring(node) or "",
            }

            for item in node.body:
                if not isinstance(item, ast.Assign):
                    continue
                for target in item.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    try:
                        literal_value = safe_literal(item.value)
                    except ValueError:
                        continue

                    if target.id == "key":
                        metadata["name"] = str(literal_value).strip().lower()
                    elif target.id == "aliases":
                        metadata["aliases"] = parse_aliases(literal_value)
                    elif target.id == "auto_help":
                        metadata["auto_help"] = bool(literal_value)
                    elif target.id == "help_category":
                        metadata["help_category"] = normalize_category(literal_value)
                    elif target.id == "auto_help_display_key":
                        metadata["name"] = str(literal_value).strip().lower()

            if not metadata["name"] or not metadata["auto_help"]:
                continue

            entry = {
                "name": metadata["name"],
                "aliases": sorted(set(metadata["aliases"])),
                "category": display_category(metadata["help_category"]),
                "category_key": metadata["help_category"],
                "kind": "command",
                "source": command_path.name,
                "usage": extract_usage(metadata["doc"], metadata["name"]),
                "summary": extract_summary(metadata["doc"]),
                "text": clean_help_text(metadata["doc"]),
            }

            for topic_name in [entry["name"], *entry["aliases"]]:
                catalog[topic_name] = entry

    return catalog


@lru_cache(maxsize=1)
def load_help_index_groups():
    tree = ast.parse(CMD_HELP_PATH.read_text(encoding="utf-8-sig"), filename=str(CMD_HELP_PATH))
    groups = {}

    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "CmdHelp":
            continue
        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_groups"):
                    groups[target.id] = safe_literal(item.value)

    return groups


def load_guide_lookup(include_staff):
    guides = {}

    for entry in list(FILE_HELP_ENTRIES.all()):
        category = normalize_category(getattr(entry, "help_category", None) or getattr(entry, "db_help_category", None))
        if not include_staff and category in PUBLIC_HIDDEN_CATEGORIES:
            continue

        key = (getattr(entry, "key", None) or getattr(entry, "db_key", "")).strip().lower()
        if not key:
            continue

        text = clean_help_text(getattr(entry, "entrytext", None) or getattr(entry, "db_entrytext", ""))
        guides[key] = {
            "name": key,
            "aliases": sorted(set(getattr(entry, "aliases", []) or [])),
            "category": display_category(category),
            "category_key": category,
            "kind": "guide",
            "source": "help-entry",
            "usage": f"help {key}",
            "summary": extract_summary(text),
            "text": text,
        }

    return guides


def topic_entry(topic_name, command_catalog, guide_lookup, kind, category_label):
    topic_key = topic_name.strip().lower()
    if kind == "command":
        entry = dict(command_catalog.get(topic_key, {}))
        if not entry:
            logger.log_warn(f"Lore help omitted missing command topic: {topic_key} ({category_label})")
            return None
        entry["category"] = category_label
        entry["category_key"] = normalize_category(category_label)
        return entry

    entry = dict(guide_lookup.get(topic_key, {}))
    if not entry:
        logger.log_warn(f"Lore help omitted missing guide topic: {topic_key} ({category_label})")
        return None
    entry["category"] = category_label
    entry["category_key"] = normalize_category(category_label)
    return entry


def build_section(section_key, group_names, include_staff, command_catalog, guide_lookup):
    groups = load_help_index_groups()
    categories = []

    for group_name in group_names:
        for category_label, topics in groups.get(group_name, OrderedDict()).items():
            normalized_category = normalize_category(category_label)
            if not include_staff and normalized_category in PUBLIC_HIDDEN_CATEGORIES:
                continue
            if not include_staff and section_key == "guides" and category_label in {"Staff Topics", "Developer Topics"}:
                continue

            entries = []
            for topic_name in topics:
                entry = topic_entry(
                    topic_name,
                    command_catalog,
                    guide_lookup,
                    "command" if section_key == "commands" else "guide",
                    category_label,
                )
                if not entry or entry.get("source") == "fallback":
                    continue
                entries.append(entry)
            if not entries:
                continue

            categories.append(
                {
                    "key": normalized_category,
                    "label": category_label,
                    "count": len(entries),
                    "entries": entries,
                }
            )

    return categories

def build_grouped_payload(include_staff):
    command_catalog = load_command_catalog()
    guide_lookup = load_guide_lookup(include_staff)

    return {
        "sections": [
            {
                "key": "commands",
                "label": SECTION_LABELS["commands"],
                "categories": build_section(
                    "commands",
                    ["page_one_groups", "fieldcraft_groups", "system_groups", "staff_groups", "advanced_groups"],
                    include_staff,
                    command_catalog,
                    guide_lookup,
                ),
            }
            ,
            {
                "key": "guides",
                "label": SECTION_LABELS["guides"],
                "categories": build_section(
                    "guides",
                    ["topic_groups"],
                    include_staff,
                    command_catalog,
                    guide_lookup,
                ),
            },
        ]
    }


load_help_index_groups()
load_command_catalog()


class LorePageView(TemplateView):
    template_name = "website/lore.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        include_staff = bool(getattr(self.request.user, "is_staff", False))
        context["lore_help_payload"] = build_grouped_payload(include_staff)
        return context


class LoreHelpApiView(View):
    def get(self, request, *args, **kwargs):
        include_staff = bool(getattr(request.user, "is_staff", False))
        return JsonResponse(build_grouped_payload(include_staff))