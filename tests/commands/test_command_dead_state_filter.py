import os
import unittest
from unittest.mock import MagicMock, patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.command import Command


class DeadStateFilterTests(unittest.TestCase):
    def _make_caller(self, *, dead, admin):
        caller = MagicMock()
        caller.is_dead.return_value = dead
        caller.is_asleep.return_value = False
        caller.account = MagicMock()
        caller.account.check_permstring.side_effect = lambda permission: admin and permission in {"Admin", "Developer"}
        return caller

    def _make_command(self, caller, key):
        cmd = Command()
        cmd.caller = caller
        cmd.key = key
        cmd.cmdstring = key
        return cmd

    @patch("commands.command.BaseCommand.at_pre_cmd", return_value=None)
    def test_dead_nonadmin_renew_blocked(self, _mock_super):
        caller = self._make_caller(dead=True, admin=False)
        result = self._make_command(caller, "renew").at_pre_cmd()
        self.assertTrue(result)
        caller.msg.assert_called_once_with(
            "You are dead. You can still look, speak, check your state, depart, or wait for resurrection."
        )

    @patch("commands.command.BaseCommand.at_pre_cmd", return_value=None)
    def test_dead_admin_renew_allowed(self, _mock_super):
        caller = self._make_caller(dead=True, admin=True)
        result = self._make_command(caller, "renew").at_pre_cmd()
        self.assertFalse(bool(result))
        caller.msg.assert_not_called()

    @patch("commands.command.BaseCommand.at_pre_cmd", return_value=None)
    def test_dead_nonadmin_look_allowed(self, _mock_super):
        caller = self._make_caller(dead=True, admin=False)
        result = self._make_command(caller, "look").at_pre_cmd()
        self.assertFalse(bool(result))
        caller.msg.assert_not_called()

    @patch("commands.command.BaseCommand.at_pre_cmd", return_value=None)
    def test_living_admin_renew_allowed(self, _mock_super):
        caller = self._make_caller(dead=False, admin=True)
        result = self._make_command(caller, "renew").at_pre_cmd()
        self.assertFalse(bool(result))
        caller.msg.assert_not_called()