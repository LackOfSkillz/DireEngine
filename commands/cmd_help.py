from collections import OrderedDict

from evennia.commands.default.help import CmdHelp as EvenniaCmdHelp
from evennia.utils.utils import pad


class CmdHelp(EvenniaCmdHelp):
    """Polished help index with player-first grouping and fixed page breaks."""

    help_page_lines = 25
    help_footer_reserve = 4
    section_indent = "  "

    page_one_groups = OrderedDict(
        (
            ("Communication", ("help", "look", "say", "whisper", "pose", "nick")),
            ("Character", ("abilities", "ability", "assess", "center", "circle", "depart", "diagnose", "favor", "heal", "injuries", "link", "manipulate", "mend", "mindstate", "perceive", "pray", "purge", "redirect", "release", "resurrect", "sacrifice", "skills", "stabilize", "states", "stats", "take", "touch", "unity", "use", "xp")),
            ("Inventory & Equipment", ("inventory", "get", "give", "drop", "draw", "stow", "wear", "remove", "wield", "unwield", "slots")),
            ("Combat", ("attack", "aim", "berserk", "fire", "load", "pounce", "reposition", "recover", "roar", "snipe", "target", "stance", "advance", "retreat", "disengage", "tend")),
        )
    )

    def func(self):
        query = str(self.args or "").strip().lower()
        if query == "warrior":
            if hasattr(self.caller, "get_warrior_help_text"):
                self.msg_help(self.caller.get_warrior_help_text())
                return
        super().func()

    system_groups = OrderedDict(
        (
            ("System", ("home", "setdesc", "access")),
        )
    )

    fieldcraft_groups = OrderedDict(
        (
            ("Awareness", ("observe", "search")),
            (
                "Stealth",
                (
                    "blend",
                    "mark",
                    "khri",
                    "hide",
                    "unhide",
                    "disguise",
                    "sneak",
                    "stalk",
                    "ambush",
                    "steal",
                    "slip",
                    "thug",
                    "find passage",
                    "enter passage",
                    "passage travel",
                ),
            ),
            ("Survival", ("analyze", "beseech", "companion", "cover tracks", "focus", "follow trail", "forage", "harvest", "hunt", "inspect", "open", "read land", "scout", "track", "climb", "swim", "skin", "pick", "disarm", "settrap", "rework")),
        )
    )

    topic_groups = OrderedDict(
        (
            ("Start Here", ("getting started", "getting_started")),
            ("Game Systems", ("character", "equipment", "combat", "fieldcraft")),
            ("Staff Topics", ("training gear",)),
            ("Developer Topics", ("evennia",)),
        )
    )

    staff_groups = OrderedDict(
        (
            ("Spawn Tools", ("spawnnpc", "spawnweapon", "spawnwearable", "spawnsheath", "spawnbox", "spawnlockpick", "spawnvendor")),
            ("Admin Tools", ("ban", "boot", "creeper", "emit", "perm", "renew", "survivaldebug", "unban", "wall")),
            ("World Building", ("@open", "alias", "batchcode", "batchcommands", "cmdsets", "copy", "cpattr", "create", "desc", "destroy", "dig", "examine", "find", "force", "link", "lock", "mvattr", "name", "set", "sethelp", "sethome", "spawn", "tag", "teleport", "tunnel", "typeclass", "unlink", "wipe")),
        )
    )

    advanced_groups = OrderedDict(
        (
            ("Server", ("about", "accounts", "objects", "server", "service", "tasks", "tickers", "time")),
            ("Scripting", ("py", "scripts")),
            ("Magic", ("prepare", "cast", "charge", "channel", "stopcast")),
            ("Economy & Trade", ("buy", "sell", "haggle", "appraise", "compare")),
            ("Social & Network", ("page", "who", "ic", "ooc", "discord2chan", "irc2chan", "ircstatus", "grapevine2chan")),
            ("System / Core", ("quit", "reload", "shutdown", "reset", "option", "password", "sessions", "userpassword")),
            ("Training & Lore", ("guild", "join", "profession", "study", "teach", "train", "endteach", "recall", "assessstance")),
        )
    )

    def _heading(self, title, width):
        return f"|c{pad(f' {title} ', width=width, fillchar='-')}|n"

    def _client_height(self):
        if self.session:
            if hasattr(self.session, "get_client_size"):
                return self.session.get_client_size()[1]
            return self.session.protocol_flags.get("SCREENHEIGHT", {0: self.help_page_lines})[0]
        return self.help_page_lines

    def _client_page_lines(self):
        return max(10, self._client_height() - self.help_footer_reserve)

    def _clickify(self, topic, click_topics):
        if click_topics:
            return f"|lchelp {topic}|lt{topic}|le"
        return topic

    def _collect_named_topics(self, available_topics, names, used_topics):
        topics = []
        for name in names:
            if name in available_topics and name not in used_topics:
                topics.append(name)
                used_topics.add(name)
        return topics

    def _format_topic_lines(self, label, topics, click_topics):
        if not topics:
            return []

        width = max(20, self.client_width())
        prefix_plain = f"{label}: "
        prefix_rendered = f"|c{label}:|n "
        continuation_plain = " " * len(prefix_plain)
        continuation_rendered = continuation_plain

        lines = []
        current_plain = prefix_plain
        current_rendered = prefix_rendered

        for index, topic in enumerate(topics):
            separator = "" if index == 0 or current_plain == continuation_plain else ", "
            plain_piece = f"{separator}{topic}"
            rendered_piece = f"{separator}{self._clickify(topic, click_topics)}"

            if len(current_plain) + len(plain_piece) > width and current_plain.strip() not in {prefix_plain.strip(), continuation_plain.strip()}:
                lines.append(current_rendered.rstrip())
                current_plain = continuation_plain + topic
                current_rendered = continuation_rendered + self._clickify(topic, click_topics)
                continue

            current_plain += plain_piece
            current_rendered += rendered_piece

        if current_rendered.strip():
            lines.append(current_rendered.rstrip())

        return lines

    def _format_fieldcraft_lines(self, groups, available_topics, click_topics, used_topics):
        lines = ["|cFieldcraft:|n"]

        for label, names in groups.items():
            topics = self._collect_named_topics(available_topics, names, used_topics)
            formatted_lines = self._format_topic_lines(label, topics, click_topics)
            if not formatted_lines:
                continue

            for line in formatted_lines:
                lines.append(f"{self.section_indent}{line}")

        return lines

    def _format_named_section(self, label, topics, click_topics, indent=""):
        return [f"{indent}{line}" for line in self._format_topic_lines(label, topics, click_topics)]

    def _build_page(self, title, sections, intro=None):
        lines = []
        if title:
            lines.append(self._heading(title, self.client_width()))
        if intro:
            lines.extend(intro)

        for section in sections:
            if not section:
                continue
            if lines:
                lines.append("")
            lines.extend(section)

        return "\n".join(lines)

    def _pack_blocks(self, blocks, intro_lines=None):
        page_limit = self._client_page_lines()
        pages = []
        current_page = list(intro_lines or [])

        def flush_page():
            if current_page:
                pages.append("\n".join(current_page).rstrip())
                current_page.clear()

        for block in blocks:
            if not block:
                continue

            block_lines = block.split("\n")
            spacer = 1 if current_page else 0

            if current_page and len(current_page) + spacer + len(block_lines) > page_limit:
                flush_page()

            if current_page:
                current_page.append("")
            current_page.extend(block_lines)

        flush_page()
        return "\f".join(page for page in pages if page)

    def _collect_group_lines(self, groups, available_topics, click_topics, used_topics, indent=""):
        lines = []

        for label, names in groups.items():
            topics = self._collect_named_topics(available_topics, names, used_topics)
            if not topics:
                continue
            if lines:
                lines.append("")
            lines.extend(self._format_named_section(label, topics, click_topics, indent=indent))

        return lines

    def _paginate_help_text(self, text):
        page_limit = self._client_page_lines()
        pages = []
        for raw_page in text.split("\f"):
            lines = raw_page.split("\n")
            current_page = []

            def flush_page():
                if current_page:
                    pages.append("\n".join(current_page).rstrip())
                    current_page.clear()

            for index, line in enumerate(lines):
                is_heading = line.startswith("|c---")
                if is_heading and len(current_page) >= page_limit - 1:
                    flush_page()

                current_page.append(line)
                if len(current_page) >= page_limit:
                    next_line = lines[index + 1] if index + 1 < len(lines) else None
                    if next_line and next_line.startswith("|c") and next_line.endswith(":|n "):
                        continue
                    flush_page()

            flush_page()

        return "\f".join(page for page in pages if page)

    def _format_root_index(self, cmd_help_dict, db_help_dict, click_topics):
        command_topics = {topic for topics in cmd_help_dict.values() for topic in topics}
        help_topics = {topic for topics in db_help_dict.values() for topic in topics}
        used_commands = set()
        used_help_topics = set()

        page_one_sections = self._collect_group_lines(
            self.page_one_groups,
            command_topics,
            click_topics,
            used_commands,
        )
        fieldcraft_section = self._format_fieldcraft_lines(
            self.fieldcraft_groups,
            command_topics,
            click_topics,
            used_commands,
        )
        system_section = self._collect_group_lines(
            self.system_groups,
            command_topics,
            click_topics,
            used_commands,
        )
        if fieldcraft_section and len(fieldcraft_section) > 1:
            page_one_sections.extend([""] + fieldcraft_section)
        if system_section:
            page_one_sections.extend([""] + system_section)

        page_one_block = "\n".join(page_one_sections)

        guides_section = self._collect_group_lines(
            OrderedDict((("Guides & Reference", tuple(topic for names in self.topic_groups.values() for topic in names)),)),
            help_topics,
            click_topics,
            used_help_topics,
        )
        staff_section = self._collect_group_lines(
            self.staff_groups,
            command_topics,
            click_topics,
            used_commands,
        )
        page_two_block = self._build_page(
            "Guides & Builder",
            [guides_section, staff_section],
        )

        advanced_section = self._collect_group_lines(
            self.advanced_groups,
            command_topics,
            click_topics,
            used_commands,
        )
        page_three_block = self._build_page(
            "Systems & Advanced Gameplay",
            [advanced_section],
        )

        return self._pack_blocks(
            [page_one_block, page_two_block, page_three_block],
            intro_lines=[
                self._heading("Help Index", self.client_width()),
                "Use |whelp <topic>|n for detailed help on a command or guide.",
                "Use |wn|n and |wp|n to move between pages.",
            ],
        )

    def _format_category_index(self, cmd_help_dict, db_help_dict, click_topics):
        width = self.client_width()
        lines = []

        for category, topics in sorted(cmd_help_dict.items()):
            entries = sorted(set(topics))
            if not entries:
                continue
            lines.append(self._heading(f"{category.title()} Commands", width))
            lines.extend(self._format_topic_lines("Commands", entries, click_topics))
            lines.append("")

        for category, topics in sorted(db_help_dict.items()):
            entries = sorted(set(topics))
            if not entries:
                continue
            lines.append(self._heading(f"{category.title()} Topics", width))
            lines.extend(self._format_topic_lines("Topics", entries, click_topics))
            lines.append("")

        if lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    def format_help_index(
        self, cmd_help_dict=None, db_help_dict=None, title_lone_category=False, click_topics=True
    ):
        cmd_help_dict = cmd_help_dict or {}
        db_help_dict = db_help_dict or {}

        total_categories = len([category for category, topics in cmd_help_dict.items() if topics])
        total_categories += len([category for category, topics in db_help_dict.items() if topics])

        if title_lone_category or total_categories <= 2:
            return self._format_category_index(cmd_help_dict, db_help_dict, click_topics)

        return self._format_root_index(cmd_help_dict, db_help_dict, click_topics)

    def msg_help(self, text, **kwargs):
        if isinstance(text, str):
            text = self._paginate_help_text(text)
        super().msg_help(text, **kwargs)