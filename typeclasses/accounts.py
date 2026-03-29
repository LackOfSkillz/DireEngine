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

from django.conf import settings
from django.utils.translation import gettext as _

from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.objects.models import ObjectDB
from evennia.utils.utils import mod_import


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
            self.msg(self.at_look(target=self.characters, session=session), session=session)
            return

        if settings.AUTO_PUPPET_ON_LOGIN:
            for candidate in self.get_auto_puppet_candidates():
                try:
                    self.puppet_object(session, candidate)
                    self.db._last_puppet = candidate
                    return
                except RuntimeError:
                    continue

            self.msg(_("No playable character could be auto-selected."), session=session)
            self.msg(self.at_look(target=self.characters, session=session), session=session)
            return

        self.msg(self.at_look(target=self.characters, session=session), session=session)

    def at_post_create_character(self, character, **kwargs):
        super().at_post_create_character(character, **kwargs)

        start_room = ObjectDB.objects.filter(id=2).first()
        if not start_room or not character:
            return

        character.home = start_room
        character.location = start_room


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
