from typeclasses.npcs import NPC


class OnboardingGuide(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_onboarding_guide = True
        self.db.is_training_dummy = False

    def at_player_enter(self, player):
        if not player:
            return False
        from systems import onboarding

        line = onboarding.get_room_prompt(player, room=getattr(self, "location", None))
        if not line:
            return False
        return onboarding.emit_npc_line(player, self, line)