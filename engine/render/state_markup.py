from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from evennia.utils import logger

from world.calendar import get_current_season, get_current_time_of_day
from world.invasion import get_current_invasion
from world.weather import get_current_weather


_MARKUP_PREFIX = "$state("
_PREVIEW_LIMIT = 120


@dataclass(frozen=True)
class TextNode:
    text: str


@dataclass(frozen=True)
class StateNode:
    group: str
    values: tuple[str, ...]
    content: str


@dataclass(frozen=True)
class ParseError:
    message: str
    offset: int


@dataclass(frozen=True)
class ParseResult:
    ast: tuple[TextNode | StateNode, ...]
    errors: tuple[ParseError, ...]


@dataclass(frozen=True)
class RenderContext:
    room: object | None
    looker: object | None = None
    zone_id: str = ""


def _normalize_text(value) -> str:
    return str(value or "").strip().lower()


def _preview_text(text: str) -> str:
    preview = str(text or "").replace("\n", "\\n")
    if len(preview) > _PREVIEW_LIMIT:
        return f"{preview[:_PREVIEW_LIMIT]}..."
    return preview


def _find_fragment_end(text: str, start: int) -> int:
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == ")":
            return index
    return -1


def _parse_state_fragment(inner: str, offset: int) -> tuple[StateNode | None, ParseError | None]:
    if "," not in inner:
        return None, ParseError("Missing comma in $state fragment.", offset)

    header, content = inner.split(",", 1)
    if ":" not in header:
        return None, ParseError("Missing group/value separator in $state fragment.", offset)

    group_text, values_text = header.split(":", 1)
    group = _normalize_text(group_text)
    raw_values = [str(value).strip().lower() for value in str(values_text or "").split("|")]
    if not group:
        return None, ParseError("Empty state group in $state fragment.", offset)
    if not raw_values or any(not value for value in raw_values):
        return None, ParseError("Empty state value in $state fragment.", offset)
    if _MARKUP_PREFIX in content:
        return None, ParseError("Nested $state fragments are not supported.", offset)
    values = tuple(raw_values)
    rendered_content = content.replace("\\)", ")")
    return StateNode(group=group, values=values, content=rendered_content), None


def parse_state_markup(text: str) -> ParseResult:
    source = str(text or "")
    if not source:
        return ParseResult(ast=(), errors=())

    ast: list[TextNode | StateNode] = []
    errors: list[ParseError] = []
    cursor = 0

    while cursor < len(source):
        marker = source.find(_MARKUP_PREFIX, cursor)
        if marker == -1:
            tail = source[cursor:]
            if tail:
                ast.append(TextNode(tail))
            break

        if marker > cursor:
            ast.append(TextNode(source[cursor:marker]))

        fragment_start = marker + len(_MARKUP_PREFIX)
        fragment_end = _find_fragment_end(source, fragment_start)
        if fragment_end == -1:
            errors.append(ParseError("Unbalanced $state fragment.", marker))
            break

        node, error = _parse_state_fragment(source[fragment_start:fragment_end], marker)
        if node is not None:
            ast.append(node)
        if error is not None:
            errors.append(error)
        cursor = fragment_end + 1

    return ParseResult(ast=tuple(ast), errors=tuple(errors))


@lru_cache(maxsize=2048)
def get_cached_parse_result(text: str) -> ParseResult:
    return parse_state_markup(text)


def clear_parse_cache() -> None:
    get_cached_parse_result.cache_clear()


def get_parse_cache_info():
    return get_cached_parse_result.cache_info()


def build_render_context(room, looker=None) -> RenderContext:
    zone_id = str(getattr(getattr(room, "db", None), "zone_id", "") or "").strip()
    return RenderContext(room=room, looker=looker, zone_id=zone_id)


def _weather_query(context: RenderContext) -> str | None:
    if not context.zone_id:
        return None
    return _normalize_text(get_current_weather(context.zone_id))


def _invasion_query(context: RenderContext) -> str | None:
    if not context.zone_id:
        return None
    return _normalize_text(get_current_invasion(context.zone_id))


def _season_query(_context: RenderContext) -> str | None:
    return _normalize_text(get_current_season())


def _time_query(_context: RenderContext) -> str | None:
    return _normalize_text(get_current_time_of_day())


STATE_GROUPS: dict[str, Callable[[RenderContext], str | None]] = {
    "weather": _weather_query,
    "invasion": _invasion_query,
    "season": _season_query,
    "time": _time_query,
}


def _source_label(context: RenderContext, description_text: str) -> str:
    room = context.room
    room_key = str(getattr(room, "key", "unknown") or "unknown")
    room_id = getattr(room, "id", None)
    room_label = f"{room_key}(#{room_id})" if room_id is not None else room_key
    return f"room={room_label} preview={_preview_text(description_text)!r}"


def _log_parse_errors(parse_result: ParseResult, context: RenderContext, description_text: str) -> None:
    if not parse_result.errors:
        return
    source = _source_label(context, description_text)
    for error in parse_result.errors:
        logger.log_warn(f"[StateMarkup] Stripped malformed fragment for {source}: {error.message}")


def _resolve_group_value(group: str, context: RenderContext, description_text: str) -> str | None:
    source = _source_label(context, description_text)
    query = STATE_GROUPS.get(group)
    if query is None:
        logger.log_warn(f"[StateMarkup] Unknown state group '{group}' for {source}.")
        return None
    try:
        return _normalize_text(query(context))
    except Exception as error:
        logger.log_warn(f"[StateMarkup] State group '{group}' failed for {source}: {error}")
        return None


def render_state_markup_ast(ast: tuple[TextNode | StateNode, ...], context: RenderContext, *, description_text: str = "") -> str:
    rendered: list[str] = []
    for node in ast:
        if isinstance(node, TextNode):
            rendered.append(node.text)
            continue
        current = _resolve_group_value(node.group, context, description_text)
        if current and current in node.values:
            rendered.append(node.content)
    return "".join(rendered)


def render_state_markup(text: str, context: RenderContext) -> str:
    description_text = str(text or "")
    parse_result = get_cached_parse_result(description_text)
    _log_parse_errors(parse_result, context, description_text)
    return render_state_markup_ast(parse_result.ast, context, description_text=description_text)