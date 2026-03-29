"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds

from commands.cmd_analyze import CmdAnalyze
from commands.cmd_appraise import CmdAppraise
from commands.cmd_assessstance import CmdAssessStance
from commands.cmd_attack import CmdAttack
from commands.cmd_advance import CmdAdvance
from commands.cmd_aim import CmdAim
from commands.cmd_abilities import CmdAbilities
from commands.cmd_ability import CmdAbility
from commands.cmd_ability_nomatch import CmdAbilityNoMatch
from commands.cmd_cast import CmdCast
from commands.cmd_clickmove import CmdClickMove
from commands.cmd_buy import CmdBuy
from commands.cmd_charge import CmdCharge
from commands.cmd_climb import CmdClimb
from commands.cmd_compare import CmdCompare
from commands.cmd_disarm import CmdDisarm
from commands.cmd_draw import CmdDraw
from commands.cmd_endteach import CmdEndTeach
from commands.cmd_forage import CmdForage
from commands.cmd_get import CmdGet
from commands.cmd_guild import CmdGuild
from commands.cmd_harvest import CmdHarvest
from commands.cmd_haggle import CmdHaggle
from commands.cmd_disengage import CmdDisengage
from commands.cmd_diagnose import CmdDiagnose
from commands.cmd_drop import CmdDrop
from commands.cmd_heal import CmdHeal
from commands.cmd_help import CmdHelp
from commands.cmd_injuries import CmdInjuries
from commands.cmd_inspect import CmdInspect
from commands.cmd_inventory import CmdInventory
from commands.cmd_ic import CmdIC
from commands.cmd_justice import CmdJustice
from commands.cmd_join import CmdJoin
from commands.cmd_bounty import CmdBounty
from commands.cmd_bounties import CmdBounties
from commands.cmd_acceptbounty import CmdAcceptBounty
from commands.cmd_bribe import CmdBribe
from commands.cmd_capture import CmdCapture
from commands.cmd_laylow import CmdLayLow
from commands.cmd_mindstate import CmdMindstate
from commands.cmd_maptest import CmdMapTest
from commands.cmd_hide import CmdHide
from commands.cmd_observe import CmdObserve
from commands.cmd_open import CmdOpen
from commands.cmd_pick import CmdPick
from commands.cmd_prepare import CmdPrepare
from commands.cmd_plead import CmdPlead
from commands.cmd_pleadrelease import CmdPleadRelease
from commands.cmd_payfine import CmdPayFine
from commands.cmd_profession import CmdProfession
from commands.cmd_recall import CmdRecall
from commands.cmd_remove import CmdRemove
from commands.cmd_renew import CmdRenew
from commands.cmd_rework import CmdRework
from commands.cmd_retreat import CmdRetreat
from commands.cmd_search import CmdSearch
from commands.cmd_sell import CmdSell
from commands.cmd_settrap import CmdSetTrap
from commands.cmd_skin import CmdSkin
from commands.cmd_skills import CmdSkills
from commands.cmd_slots import CmdSlots
from commands.cmd_spawnnpc import CmdSpawnNPC
from commands.cmd_spawnsheath import CmdSpawnSheath
from commands.cmd_spawnwearable import CmdSpawnWearable
from commands.cmd_spawnweapon import CmdSpawnWeapon
from commands.cmd_spawnbox import CmdSpawnBox
from commands.cmd_spawnlockpick import CmdSpawnLockpick
from commands.cmd_sneak import CmdSneak
from commands.cmd_spawnvendor import CmdSpawnVendor
from commands.cmd_stats import CmdStats
from commands.cmd_steal import CmdSteal
from commands.cmd_stow import CmdStow
from commands.cmd_survivaldebug import CmdSurvivalDebug
from commands.cmd_swim import CmdSwim
from commands.cmd_stalk import CmdStalk
from commands.cmd_stance import CmdStance
from commands.cmd_tend import CmdTend
from commands.cmd_target import CmdTarget
from commands.cmd_teach import CmdTeach
from commands.cmd_throw import CmdThrow
from commands.cmd_train import CmdTrain
from commands.cmd_surrender import CmdSurrender
from commands.cmd_testgodot import CmdTestGodot
from commands.cmd_track import CmdTrack
from commands.cmd_stopcast import CmdStopCast
from commands.cmd_study import CmdStudy
from commands.cmd_unhide import CmdUnhide
from commands.cmd_unwield import CmdUnwield
from commands.cmd_use import CmdUseSkill
from commands.cmd_wear import CmdWear
from commands.cmd_wield import CmdWield
from commands.cmd_ambush import CmdAmbush
from commands.cmd_creeper import CmdCreeper
from commands.cmd_states import CmdStates


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        self.add(CmdAnalyze())
        self.add(CmdAppraise())
        self.add(CmdAssessStance())
        self.add(CmdAdvance())
        self.add(CmdAim())
        self.add(CmdAbilities())
        self.add(CmdAbility())
        self.add(CmdAbilityNoMatch())
        self.add(CmdAmbush())
        self.add(CmdAttack())
        self.add(CmdBuy())
        self.add(CmdBounty())
        self.add(CmdBounties())
        self.add(CmdAcceptBounty())
        self.add(CmdBribe())
        self.add(CmdCast())
        self.add(CmdCapture())
        self.add(CmdCharge())
        self.add(CmdClickMove())
        self.add(CmdClimb())
        self.add(CmdCompare())
        self.add(CmdCreeper())
        self.add(CmdDisarm())
        self.add(CmdDraw())
        self.add(CmdEndTeach())
        self.add(CmdDiagnose())
        self.add(CmdDisengage())
        self.add(CmdDrop())
        self.add(CmdForage())
        self.add(CmdGet())
        self.add(CmdGuild())
        self.add(CmdHarvest())
        self.add(CmdHaggle())
        self.add(CmdHeal())
        self.add(CmdHelp())
        self.add(CmdHide())
        self.add(CmdInspect())
        self.add(CmdInjuries())
        self.add(CmdInventory())
        self.add(CmdJustice())
        self.add(CmdJoin())
        self.add(CmdLayLow())
        self.add(CmdMapTest())
        self.add(CmdMindstate())
        self.add(CmdObserve())
        self.add(CmdOpen())
        self.add(CmdPick())
        self.add(CmdPlead())
        self.add(CmdPleadRelease())
        self.add(CmdPayFine())
        self.add(CmdPrepare())
        self.add(CmdProfession())
        self.add(CmdRecall())
        self.add(CmdRemove())
        self.add(CmdRenew())
        self.add(CmdRework())
        self.add(CmdSearch())
        self.add(CmdSell())
        self.add(CmdSetTrap())
        self.add(CmdRetreat())
        self.add(CmdSkin())
        self.add(CmdSkills())
        self.add(CmdSlots())
        self.add(CmdSpawnNPC())
        self.add(CmdSpawnSheath())
        self.add(CmdSpawnWearable())
        self.add(CmdSpawnBox())
        self.add(CmdSpawnLockpick())
        self.add(CmdSpawnVendor())
        self.add(CmdSpawnWeapon())
        self.add(CmdSneak())
        self.add(CmdStats())
        self.add(CmdSteal())
        self.add(CmdStow())
        self.add(CmdSurrender())
        self.add(CmdStopCast())
        self.add(CmdStudy())
        self.add(CmdSurvivalDebug())
        self.add(CmdSwim())
        self.add(CmdTrack())
        self.add(CmdStalk())
        self.add(CmdStance())
        self.add(CmdStates())
        self.add(CmdTend())
        self.add(CmdTarget())
        self.add(CmdTeach())
        self.add(CmdThrow())
        self.add(CmdTrain())
        self.add(CmdTestGodot())
        self.add(CmdUnhide())
        self.add(CmdUnwield())
        self.add(CmdUseSkill())
        self.add(CmdWear())
        self.add(CmdWield())
        #
        # any commands you add below will overload the default ones.
        #


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        self.add(CmdIC())
        #
        # any commands you add below will overload the default ones.
        #


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
