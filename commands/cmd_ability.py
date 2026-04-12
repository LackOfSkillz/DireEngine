from commands.command import Command


class CmdAbility(Command):
  """
  Use a learned or visible ability.

  Examples:
    ability test
  """

  key = "ability"
  locks = "cmd:all()"
  help_category = "Character"

  def func(self):
    if not self.args:
      self.caller.msg("Use which ability?")
      return

    ability_key = self.args.strip().lower()
    self.caller.execute_ability_input(ability_key)