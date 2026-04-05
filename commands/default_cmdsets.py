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
from commands.cmd_assess import CmdAssess
from commands.cmd_assessstance import CmdAssessStance
from commands.cmd_attack import CmdAttack
from commands.cmd_berserk import CmdBerserk
from commands.cmd_beseech import CmdBeseech
from commands.cmd_disguise import CmdDisguise
from commands.cmd_advance import CmdAdvance
from commands.cmd_aim import CmdAim
from commands.cmd_abilities import CmdAbilities
from commands.cmd_ability import CmdAbility
from commands.cmd_ability_nomatch import CmdAbilityNoMatch
from commands.cmd_cast import CmdCast
from commands.cmd_clickmove import CmdClickMove
from commands.cmd_chargen import (
    CmdCharCreate,
    CmdChargenBack,
    CmdChargenBuild,
    CmdChargenCancel,
    CmdChargenConfirm,
    CmdChargenEyes,
    CmdChargenGender,
    CmdChargenHair,
    CmdChargenHeight,
    CmdChargenInspect,
    CmdChargenName,
    CmdChargenNext,
    CmdChargenRace,
    CmdChargenResetStats,
    CmdChargenSkin,
    CmdChargenStat,
)
from commands.cmd_buy import CmdBuy
from commands.cmd_charge import CmdCharge
from commands.cmd_circle import CmdCircle
from commands.cmd_climb import CmdClimb
from commands.cmd_companion import CmdCompanion
from commands.cmd_compare import CmdCompare
from commands.cmd_commune import CmdCommune
from commands.cmd_blend import CmdBlend
from commands.cmd_covertracks import CmdCoverTracks
from commands.cmd_disarm import CmdDisarm
from commands.cmd_draw import CmdDraw
from commands.cmd_endteach import CmdEndTeach
from commands.cmd_engine import CmdEngine
from commands.cmd_enterpassage import CmdEnterPassage
from commands.cmd_experience import CmdExperience
from commands.cmd_findpassage import CmdFindPassage
from commands.cmd_fire import CmdFire
from commands.cmd_favor import CmdFavor
from commands.cmd_focus import CmdFocus
from commands.cmd_followtrail import CmdFollowTrail
from commands.cmd_forage import CmdForage
from commands.cmd_get import CmdGet
from commands.cmd_guild import CmdGuild
from commands.cmd_harvest import CmdHarvest
from commands.cmd_khri import CmdKhri
from commands.cmd_haggle import CmdHaggle
from commands.cmd_hunt import CmdHunt
from commands.cmd_disengage import CmdDisengage
from commands.cmd_diagnose import CmdDiagnose
from commands.cmd_depart import CmdDepart
from commands.cmd_death import CmdDeath
from commands.cmd_die import CmdDie
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
from commands.cmd_load import CmdLoad
from commands.cmd_loot import CmdLoot
from commands.cmd_link import CmdLink
from commands.cmd_manipulate import CmdManipulate
from commands.cmd_mark import CmdMark
from commands.cmd_mend import CmdMend
from commands.cmd_mindstate import CmdMindstate
from commands.cmd_maptest import CmdMapTest
from commands.cmd_hide import CmdHide
from commands.cmd_observe import CmdObserve
from commands.cmd_onboarding import CmdOnboardingGender, CmdOnboardingIntake, CmdOnboardingName, CmdOnboardingSet, CmdOnboardingStand
from commands.cmd_open import CmdOpen
from commands.cmd_pick import CmdPick
from commands.cmd_pounce import CmdPounce
from commands.cmd_prepare import CmdPrepare
from commands.cmd_plead import CmdPlead
from commands.cmd_pleadrelease import CmdPleadRelease
from commands.cmd_payfine import CmdPayFine
from commands.cmd_passagetravel import CmdPassageTravel
from commands.cmd_perceive import CmdPerceive
from commands.cmd_preserve import CmdPreserve
from commands.cmd_pray import CmdPray
from commands.cmd_purge import CmdPurge
from commands.cmd_profession import CmdProfession
from commands.cmd_reposition import CmdReposition
from commands.cmd_recall import CmdRecall
from commands.cmd_consent import CmdConsent
from commands.cmd_corpse import CmdCorpse
from commands.cmd_redirect import CmdRedirect
from commands.cmd_racemods import CmdRaceMods
from commands.cmd_race import CmdRace
from commands.cmd_release import CmdRelease
from commands.cmd_resurrect import CmdResurrect
from commands.cmd_readland import CmdReadLand
from commands.cmd_remove import CmdRemove
from commands.cmd_recover import CmdRecover
from commands.cmd_rejuvenate import CmdRejuvenate
from commands.cmd_renew import CmdRenew
from commands.cmd_rework import CmdRework
from commands.cmd_roar import CmdRoar
from commands.cmd_scout import CmdScout
from commands.cmd_retreat import CmdRetreat
from commands.cmd_search import CmdSearch
from commands.cmd_sell import CmdSell
from commands.cmd_shop import CmdShop
from commands.cmd_sensesoul import CmdSenseSoul
from commands.cmd_settrap import CmdSetTrap
from commands.cmd_setcircle import CmdSetCircle
from commands.cmd_setrace import CmdSetRace
from commands.cmd_skilldebug import CmdSkillDebug
from commands.cmd_selfreturn import CmdSelfReturn
from commands.cmd_skin import CmdSkin
from commands.cmd_skills import CmdSkills
from commands.cmd_slots import CmdSlots
from commands.cmd_sacrifice import CmdSacrifice
from commands.cmd_spawnnpc import CmdSpawnNPC
from commands.cmd_spawnsheath import CmdSpawnSheath
from commands.cmd_spawnwearable import CmdSpawnWearable
from commands.cmd_spawnweapon import CmdSpawnWeapon
from commands.cmd_spawnbox import CmdSpawnBox
from commands.cmd_spawnlockpick import CmdSpawnLockpick
from commands.cmd_sneak import CmdSneak
from commands.cmd_spawnvendor import CmdSpawnVendor
from commands.cmd_stats import CmdStats
from commands.cmd_stabilize import CmdStabilize
from commands.cmd_steal import CmdSteal
from commands.cmd_stow import CmdStow
from commands.cmd_survivaldebug import CmdSurvivalDebug
from commands.cmd_swim import CmdSwim
from commands.cmd_snipe import CmdSnipe
from commands.cmd_stalk import CmdStalk
from commands.cmd_stance import CmdStance
from commands.cmd_slip import CmdSlip
from commands.cmd_tend import CmdTend
from commands.cmd_take import CmdTake
from commands.cmd_target import CmdTarget
from commands.cmd_teach import CmdTeach
from commands.cmd_center import CmdCenter
from commands.cmd_touch import CmdTouch
from commands.cmd_throw import CmdThrow
from commands.cmd_train import CmdTrain
from commands.cmd_surrender import CmdSurrender
from commands.cmd_testgodot import CmdTestGodot
from commands.cmd_timingaudit import CmdTimingAudit
from commands.cmd_track import CmdTrack
from commands.cmd_stopcast import CmdStopCast
from commands.cmd_study import CmdStudy
from commands.cmd_unhide import CmdUnhide
from commands.cmd_unity import CmdUnity
from commands.cmd_unwield import CmdUnwield
from commands.cmd_use import CmdUseSkill
from commands.cmd_uncurse import CmdUncurse
from commands.cmd_unlock import CmdUnlock
from commands.cmd_wear import CmdWear
from commands.cmd_wield import CmdWield
from commands.cmd_xp import CmdXP
from commands.cmd_ambush import CmdAmbush
from commands.cmd_balance import CmdBalance
from commands.cmd_deposit import CmdDeposit
from commands.cmd_creeper import CmdCreeper
from commands.cmd_decaycorpse import CmdDecayCorpse
from commands.cmd_retrieve import CmdRetrieve
from commands.cmd_deathinspect import CmdDeathInspect
from commands.cmd_store import CmdStore
from commands.cmd_res import CmdRes
from commands.cmd_states import CmdStates
from commands.cmd_thug import CmdThug
from commands.cmd_withdraw import CmdWithdraw


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
        self.add(CmdAssess())
        self.add(CmdAssessStance())
        self.add(CmdAdvance())
        self.add(CmdAim())
        self.add(CmdAbilities())
        self.add(CmdAbility())
        self.add(CmdAbilityNoMatch())
        self.add(CmdAmbush())
        self.add(CmdAttack())
        self.add(CmdBalance())
        self.add(CmdBeseech())
        self.add(CmdBlend())
        self.add(CmdBerserk())
        self.add(CmdBuy())
        self.add(CmdBounty())
        self.add(CmdBounties())
        self.add(CmdAcceptBounty())
        self.add(CmdBribe())
        self.add(CmdCast())
        self.add(CmdCapture())
        self.add(CmdCenter())
        self.add(CmdCharge())
        self.add(CmdCircle())
        self.add(CmdCommune())
        self.add(CmdClickMove())
        self.add(CmdClimb())
        self.add(CmdCompanion())
        self.add(CmdCompare())
        self.add(CmdConsent())
        self.add(CmdCorpse())
        self.add(CmdCoverTracks())
        self.add(CmdCreeper())
        self.add(CmdDecayCorpse())
        self.add(CmdDisarm())
        self.add(CmdDraw())
        self.add(CmdEnterPassage())
        self.add(CmdEndTeach())
        self.add(CmdEngine())
        self.add(CmdDiagnose())
        self.add(CmdDeath())
        self.add(CmdDeathInspect())
        self.add(CmdDepart())
        self.add(CmdDeposit())
        self.add(CmdDie())
        self.add(CmdDisguise())
        self.add(CmdDisengage())
        self.add(CmdDrop())
        self.add(CmdFavor())
        self.add(CmdFire())
        self.add(CmdFocus())
        self.add(CmdForage())
        self.add(CmdFindPassage())
        self.add(CmdFollowTrail())
        self.add(CmdGet())
        self.add(CmdGuild())
        self.add(CmdHarvest())
        self.add(CmdHaggle())
        self.add(CmdHeal())
        self.add(CmdHelp())
        self.add(CmdHide())
        self.add(CmdHunt())
        self.add(CmdInspect())
        self.add(CmdInjuries())
        self.add(CmdInventory())
        self.add(CmdJustice())
        self.add(CmdJoin())
        self.add(CmdKhri())
        self.add(CmdLayLow())
        self.add(CmdLink())
        self.add(CmdLoad())
        self.add(CmdLoot())
        self.add(CmdManipulate())
        self.add(CmdMark())
        self.add(CmdMend())
        self.add(CmdMapTest())
        self.add(CmdMindstate())
        self.add(CmdObserve())
        self.add(CmdOnboardingGender())
        self.add(CmdOnboardingStand())
        self.add(CmdOnboardingSet())
        self.add(CmdOnboardingName())
        self.add(CmdOnboardingIntake())
        self.add(CmdOpen())
        self.add(CmdPick())
        self.add(CmdPounce())
        self.add(CmdPlead())
        self.add(CmdPleadRelease())
        self.add(CmdPayFine())
        self.add(CmdPassageTravel())
        self.add(CmdPerceive())
        self.add(CmdPreserve())
        self.add(CmdPray())
        self.add(CmdPurge())
        self.add(CmdPrepare())
        self.add(CmdProfession())
        self.add(CmdReposition())
        self.add(CmdReadLand())
        self.add(CmdRace())
        self.add(CmdRaceMods())
        self.add(CmdRecall())
        self.add(CmdRecover())
        self.add(CmdRedirect())
        self.add(CmdRetrieve())
        self.add(CmdRelease())
        self.add(CmdRemove())
        self.add(CmdRejuvenate())
        self.add(CmdResurrect())
        self.add(CmdRes())
        self.add(CmdRenew())
        self.add(CmdRework())
        self.add(CmdRoar())
        self.add(CmdScout())
        self.add(CmdSearch())
        self.add(CmdSell())
        self.add(CmdShop())
        self.add(CmdSenseSoul())
        self.add(CmdSetTrap())
        self.add(CmdSetCircle())
        self.add(CmdSetRace())
        self.add(CmdExperience())
        self.add(CmdSkillDebug())
        self.add(CmdRetreat())
        self.add(CmdSacrifice())
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
        self.add(CmdSlip())
        self.add(CmdStats())
        self.add(CmdStabilize())
        self.add(CmdSteal())
        self.add(CmdStore())
        self.add(CmdStow())
        self.add(CmdSurrender())
        self.add(CmdStopCast())
        self.add(CmdStudy())
        self.add(CmdSurvivalDebug())
        self.add(CmdSwim())
        self.add(CmdTake())
        self.add(CmdSnipe())
        self.add(CmdTrack())
        self.add(CmdTouch())
        self.add(CmdUnity())
        self.add(CmdUnlock())
        self.add(CmdStalk())
        self.add(CmdStance())
        self.add(CmdStates())
        self.add(CmdTend())
        self.add(CmdTarget())
        self.add(CmdTeach())
        self.add(CmdTimingAudit())
        self.add(CmdThrow())
        self.add(CmdTrain())
        self.add(CmdTestGodot())
        self.add(CmdUnhide())
        self.add(CmdUncurse())
        self.add(CmdUnwield())
        self.add(CmdUseSkill())
        self.add(CmdWithdraw())
        self.add(CmdXP())
        self.add(CmdWear())
        self.add(CmdWield())
        self.add(CmdThug())
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
        self.add(CmdCharCreate())
        self.add(CmdChargenName())
        self.add(CmdChargenRace())
        self.add(CmdChargenGender())
        self.add(CmdChargenStat())
        self.add(CmdChargenResetStats())
        self.add(CmdChargenBuild())
        self.add(CmdChargenHeight())
        self.add(CmdChargenHair())
        self.add(CmdChargenEyes())
        self.add(CmdChargenSkin())
        self.add(CmdChargenNext())
        self.add(CmdChargenBack())
        self.add(CmdChargenCancel())
        self.add(CmdChargenConfirm())
        self.add(CmdChargenInspect())
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
