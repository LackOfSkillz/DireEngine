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

        return onboarding.emit_state_dialogue(player)