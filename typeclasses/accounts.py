"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

from collections.abc import Mapping

from django.conf import settings
from django.utils.translation import gettext as _

from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.objects.models import ObjectDB
from evennia.utils.utils import mod_import

from systems.chargen.controller import ChargenController
from systems.chargen.flow import format_chargen_summary, render_step_prompt
from systems.chargen.validators import release_name
from systems.character.creation import CharacterCreationError, finalize_character_creation, is_onboarding_start_room, resolve_creation_start_room


class Account(DefaultAccount):
    """
    An Account is the actual OOC player entity. It doesn't exist in the game,
    but puppets characters.

    This is the base Typeclass for all Accounts. Accounts represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. An Account
    can connect to a Character Object in order to "enter" the
    game.

    Account Typeclass API:

    * Available properties (only available on initiated typeclass objects)

     - key (string) - name of account
     - name (string)- wrapper for user.username
     - aliases (list of strings) - aliases to the object. Will be saved to
            database as AliasDB entries but returned as strings.
     - dbref (int, read-only) - unique #id-number. Also "id" can be used.
     - date_created (string) - time stamp of object creation
     - permissions (list of strings) - list of permission strings
     - user (User, read-only) - django User authorization object
     - obj (Object) - game object controlled by account. 'character' can also
                     be used.
     - is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     - locks - lock-handler: use locks.add() to add new lock strings
     - db - attribute-handler: store/retrieve database attributes on this
                              self.db.myattr=val, val=self.db.myattr
     - ndb - non-persistent attribute handler: same as db but does not
                                  create a database entry when storing data
     - scripts - script-handler. Add new scripts to object with scripts.add()
     - cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     - nicks - nick-handler. New nicks with nicks.add().
     - sessions - session-handler. Use session.get() to see all sessions connected, if any
     - options - option-handler. Defaults are taken from settings.OPTIONS_ACCOUNT_DEFAULT
     - characters - handler for listing the account's playable characters

    * Helper methods (check autodocs for full updated listing)

     - msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     - execute_cmd(raw_string)
     - search(searchdata, return_puppet=False, search_object=False, typeclass=None,
                      nofound_string=None, multimatch_string=None, use_nicks=True,
                      quiet=False, **kwargs)
     - is_typeclass(typeclass, exact=False)
     - swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     - access(accessing_obj, access_type='read', default=False, no_superuser_bypass=False, **kwargs)
     - check_permstring(permstring)
     - get_cmdsets(caller, current, **kwargs)
     - get_cmdset_providers()
     - uses_screenreader(session=None)
     - get_display_name(looker, **kwargs)
     - get_extra_display_name_info(looker, **kwargs)
     - disconnect_session_from_account()
     - puppet_object(session, obj)
     - unpuppet_object(session)
     - unpuppet_all()
     - get_puppet(session)
     - get_all_puppets()
     - is_banned(**kwargs)
     - get_username_validators(validator_config=settings.AUTH_USERNAME_VALIDATORS)
     - authenticate(username, password, ip="", **kwargs)
     - normalize_username(username)
     - validate_username(username)
     - validate_password(password, account=None)
     - set_password(password, **kwargs)
     - get_character_slots()
     - get_available_character_slots()
     - create_character(*args, **kwargs)
     - create(*args, **kwargs)
     - delete(*args, **kwargs)
     - channel_msg(message, channel, senders=None, **kwargs)
     - idle_time()
     - connection_time()

    * Hook methods

     basetype_setup()
     at_account_creation()

     > note that the following hooks are also found on Objects and are
       usually handled on the character level:

     - at_init()
     - at_first_save()
     - at_access()
     - at_cmdset_get(**kwargs)
     - at_password_change(**kwargs)
     - at_first_login()
     - at_pre_login()
     - at_post_login(session=None)
     - at_failed_login(session, **kwargs)
     - at_disconnect(reason=None, **kwargs)
     - at_post_disconnect(**kwargs)
     - at_message_receive()
     - at_message_send()
     - at_server_reload()
     - at_server_shutdown()
     - at_look(target=None, session=None, **kwargs)
     - at_post_create_character(character, **kwargs)
     - at_post_add_character(char)
     - at_post_remove_character(char)
     - at_pre_channel_msg(message, channel, senders=None, **kwargs)
     - at_post_chnnel_msg(message, channel, senders=None, **kwargs)

    """

    def is_webclient_session(self, session):
        if not session:
            return False

        protocol_key = str(getattr(session, "protocol_key", "") or "").lower()
        if protocol_key.startswith("webclient/") or protocol_key in {"websocket", "ajax"}:
            return True

        return bool(getattr(session, "csessid", None))

    def clear_stale_puppet_links(self):
        for character in self.characters.all():
            if getattr(character, "account", None) == self and not character.sessions.count():
                del character.account
                character.tags.remove("puppeted", category="account")

    def get_webclient_preferred_character(self, session):
        if not self.is_webclient_session(session):
            return None

        csessid = getattr(session, "csessid", None)
        if not csessid:
            return None

        session_store = mod_import(settings.SESSION_ENGINE).SessionStore
        browser_session = session_store(session_key=csessid)
        puppet_pk = browser_session.get("puppet")
        if not puppet_pk:
            return None

        return next((char for char in self.characters.all() if getattr(char, "pk", None) == int(puppet_pk)), None)

    def set_webclient_preferred_character(self, session, character):
        if not self.is_webclient_session(session):
            return

        csessid = getattr(session, "csessid", None)
        if not csessid:
            return

        session_store = mod_import(settings.SESSION_ENGINE).SessionStore
        browser_session = session_store(session_key=csessid)
        browser_session["puppet"] = int(character.pk) if character and getattr(character, "pk", None) else None
        browser_session.save()

    def get_auto_puppet_candidates(self):
        candidates = []
        last_puppet = getattr(self.db, "_last_puppet", None)

        if getattr(last_puppet, "pk", None):
            candidates.append(last_puppet)

        for character in self.characters.all():
            if getattr(character, "pk", None) and character not in candidates:
                candidates.append(character)

        return candidates

    def get_onboarding_entry_room(self, create=False):
        room = resolve_creation_start_room(start_room=None)
        if is_onboarding_start_room(room):
            return room
        if not create:
            return None
        try:
            from server.conf.at_server_startstop import _ensure_new_player_tutorial

            room = _ensure_new_player_tutorial()
        except Exception:
            return None
        return room if is_onboarding_start_room(room) else None

    def route_character_to_onboarding(self, character, create=False):
        if not character or bool(getattr(getattr(character, "db", None), "is_npc", False)):
            return False
        state = getattr(character.db, "onboarding_state", None)
        if not isinstance(state, Mapping):
            return False
        if bool(state.get("complete", False)):
            return False

        room = getattr(character, "location", None)
        if not is_onboarding_start_room(room):
            room = self.get_onboarding_entry_room(create=create)
            if not room:
                return False
            character.home = room
            character.move_to(room, quiet=True, use_destination=False)

        try:
            from systems import onboarding

            onboarding.ensure_onboarding_state(character)
            onboarding.handle_room_entry(character)
        except Exception:
            pass
        return True

    def get_chargen_controller(self, create=False, reset=False):
        state = getattr(self.ndb, "chargen_state", None)
        if state is None and not create and not reset:
            return None
        controller = ChargenController(state=state, account=self)
        if state is None or reset:
            controller.start(reset=reset)
            self.ndb.chargen_state = controller.state
            return controller
        return controller

    def clear_chargen_state(self):
        state = getattr(self.ndb, "chargen_state", None)
        if state and getattr(state, "reserved_name", None):
            release_name(state.reserved_name)
        if hasattr(self.ndb, "chargen_state"):
            del self.ndb.chargen_state

    def handle_chargen_input(self, command, args=None):
        controller = self.get_chargen_controller(create=command in {"charcreate", "chargen"})
        if not controller:
            return {"ok": False, "error": "No active character creation session. Use 'charcreate' to begin."}
        result = controller.handle_input(command, args=args)
        self.ndb.chargen_state = controller.state
        if result.get("step") in {"complete", "cancelled"}:
            self.clear_chargen_state()
        return result

    def render_chargen_prompt(self):
        controller = self.get_chargen_controller(create=False)
        if not controller:
            return None
        return render_step_prompt(controller.state)

    def at_look(self, target=None, session=None, **kwargs):
        if target and not isinstance(target, (list, tuple)):
            return super().at_look(target=target, session=session, **kwargs)

        characters = list(entry for entry in (target or self.characters.all()) if entry)
        try:
            sessions = list(self.sessions.all())
        except Exception:
            sessions = []

        txt_header = f"Account |g{self.name}|n (Character Manager)"

        session_lines = []
        if not sessions:
            session_lines.append("- no active sessions")
        else:
            for index, sess in enumerate(sessions, start=1):
                ip_addr = sess.address[0] if isinstance(sess.address, tuple) else sess.address
                marker = "|w*|n" if session and session.sessid == sess.sessid else "-"
                session_lines.append(f"{marker} {index}. {sess.protocol_key} ({ip_addr})")
        txt_sessions = "|wConnected session(s):|n\n" + "\n".join(session_lines)

        manager_lines = [
            "|wManager Commands:|n",
            "  |wcharcreate|n begins or restarts character creation.",
            "  |wlook|n refreshes this manager screen.",
            "  |wic <name>|n enters the world with a character.",
        ]
        controller = self.get_chargen_controller(create=False)
        if controller:
            manager_lines.append("")
            manager_lines.append("|wChargen In Progress:|n")
            manager_lines.append(render_step_prompt(controller.state))
            manager_lines.append(format_chargen_summary(controller.state))
        else:
            manager_lines.append("")
            manager_lines.append("|wNo active chargen session.|n")
            if not characters:
                manager_lines.append("Create your first character with |wcharcreate|n.")
        manager_lines.append("")
        manager_lines.append("|wCareer Flow:|n new characters arrive as Commoners. Profession choice happens later in the world.")
        txt_manager = "\n".join(manager_lines)

        if not characters:
            txt_characters = "You have no characters yet. Use |wcharcreate|n to begin."
        else:
            max_chars = "unlimited" if self.is_superuser or settings.MAX_NR_CHARACTERS is None else settings.MAX_NR_CHARACTERS
            char_lines = []
            for char in characters:
                race = getattr(char.db, "race", "unknown")
                gender = getattr(char.db, "gender", "unknown")
                profession = getattr(char.db, "profession", "commoner")
                try:
                    char_sessions = list(char.sessions.all())
                except Exception:
                    char_sessions = []
                if char_sessions:
                    char_lines.append(f" - |G{char.name}|n [{race} / {gender} / {profession}] (currently active)")
                else:
                    char_lines.append(f" - {char.name} [{race} / {gender} / {profession}]")
            txt_characters = (
                f"Available character(s) ({len(characters)}/{max_chars}, |wic <name>|n to play):|n\n"
                + "\n".join(char_lines)
            )

        return self.ooc_appearance_template.format(
            header=txt_header,
            sessions=txt_sessions,
            characters=txt_manager + "\n\n" + txt_characters,
            footer="",
        )

    def at_post_login(self, session=None, **kwargs):
        if not session:
            return

        protocol_flags = self.attributes.get("_saved_protocol_flags", {})
        if protocol_flags:
            session.update_flags(**protocol_flags)

        session.msg(logged_in={})

        self._send_to_connect_channel(_("|G{key} connected|n").format(key=self.key))

        self.clear_stale_puppet_links()

        if self.get_puppet(session):
            return

        webclient_preferred = self.get_webclient_preferred_character(session)
        if self.is_webclient_session(session):
            candidates = []
            if webclient_preferred:
                candidates.append(webclient_preferred)
            for candidate in self.get_auto_puppet_candidates():
                if candidate not in candidates:
                    candidates.append(candidate)

            for candidate in candidates:
                try:
                    self.puppet_object(session, candidate)
                    self.db._last_puppet = candidate
                    self.set_webclient_preferred_character(session, candidate)
                    return
                except RuntimeError:
                    continue

            self.msg(_("No playable character could be auto-selected."), session=session)
            if not self.characters.all():
                self.msg("You have no characters yet. Type |wcharcreate|n to begin character creation.", session=session)
            self.msg(self.at_look(target=self.characters, session=session), session=session)
            return

        if settings.AUTO_PUPPET_ON_LOGIN:
            for candidate in self.get_auto_puppet_candidates():
                try:
                    self.route_character_to_onboarding(candidate, create=True)
                    self.puppet_object(session, candidate)
                    self.db._last_puppet = candidate
                    return
                except RuntimeError:
                    continue

            self.msg(_("No playable character could be auto-selected."), session=session)
            if not self.characters.all():
                self.msg("You have no characters yet. Type |wcharcreate|n to begin character creation.", session=session)
            self.msg(self.at_look(target=self.characters, session=session), session=session)
            return

        if not self.characters.all():
            self.msg("You have no characters yet. Type |wcharcreate|n to begin character creation.", session=session)
        self.msg(self.at_look(target=self.characters, session=session), session=session)

    def create_character(self, *args, **kwargs):
        creation_blueprint = kwargs.pop("creation_blueprint", None)
        race = kwargs.pop("race", None)
        gender = kwargs.pop("gender", None)
        profession = kwargs.pop("profession", None)
        stats = kwargs.pop("stats", None)
        description = kwargs.pop("description", None)
        start_room = kwargs.pop("start_room", None)

        character, errors = super().create_character(*args, **kwargs)
        if errors or not character:
            return character, errors

        try:
            finalize_character_creation(
                character,
                blueprint=creation_blueprint,
                race=race,
                gender=gender,
                profession=profession,
                stats=stats,
                description=description,
                start_room=start_room,
            )
        except CharacterCreationError as exc:
            character.delete()
            return None, [str(exc)]
        except Exception as exc:
            character.delete()
            return None, [f"Character creation failed during finalization: {exc}"]

        return character, errors

    def at_post_create_character(self, character, **kwargs):
        super().at_post_create_character(character, **kwargs)
        room = self.get_onboarding_entry_room(create=True)
        if not room:
            return
        try:
            from systems import onboarding

            state = onboarding.ensure_onboarding_state(character)
            state["active"] = True
            state["complete"] = False
            character.db.onboarding_state = state
        except Exception:
            character.db.onboarding_state = {"active": True, "complete": False}
        character.home = room
        character.move_to(room, quiet=True, use_destination=False)
        self.route_character_to_onboarding(character, create=False)


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
