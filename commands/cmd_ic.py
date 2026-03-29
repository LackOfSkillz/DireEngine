import re

from evennia import search_object
from evennia.commands.default.account import CmdIC as BaseCmdIC
from evennia.utils import logger


_DBREF_RE = re.compile(r"#(\d+)")


class CmdIC(BaseCmdIC):
    def _find_playable_candidates(self, account, raw_query):
        query = (raw_query or "").strip()
        playables = [character for character in account.characters.all() if character]
        if not query:
            return [account.db._last_puppet] if getattr(account.db, "_last_puppet", None) else []

        dbref_match = _DBREF_RE.search(query)
        if dbref_match:
            target_id = int(dbref_match.group(1))
            return [character for character in playables if getattr(character, "id", None) == target_id]

        exact_matches = [character for character in playables if character.key.lower() == query.lower()]
        if exact_matches:
            return exact_matches

        partial_matches = [character for character in playables if query.lower() in character.key.lower()]
        if partial_matches:
            return partial_matches

        multimatch = re.match(r"^(?P<name>.+)-(?P<index>\d+)$", query)
        if multimatch:
            name = multimatch.group("name").strip().lower()
            index = max(1, int(multimatch.group("index"))) - 1
            named_matches = [character for character in playables if character.key.lower() == name]
            if 0 <= index < len(named_matches):
                return [named_matches[index]]
            return []

        return []

    def func(self):
        account = self.account
        session = self.session

        character_candidates = self._find_playable_candidates(account, self.args)

        if not character_candidates and self.args and account.locks.check_lockstring(account, "perm(Builder)"):
            global_matches = [
                character
                for character in search_object(self.args)
                if character.access(account, "puppet")
            ]
            character_candidates.extend(global_matches)

        if not character_candidates:
            if self.args:
                self.msg("That is not a valid character choice.")
            else:
                self.msg("Usage: ic <character>")
            return

        if len(character_candidates) > 1:
            self.msg(
                "Multiple targets with the same name:\n %s"
                % ", ".join("%s(#%s)" % (obj.key, obj.id) for obj in character_candidates)
            )
            return

        new_character = character_candidates[0]

        try:
            account.puppet_object(session, new_character)
            account.db._last_puppet = new_character
            logger.log_sec(
                f"Puppet Success: (Caller: {account}, Target: {new_character}, IP:"
                f" {self.session.address})."
            )
        except RuntimeError as exc:
            self.msg(f"|rYou cannot become |C{new_character.name}|n: {exc}")
            logger.log_sec(
                f"Puppet Failed: %s (Caller: {account}, Target: {new_character}, IP:"
                f" {self.session.address})."
            )