# UTILITY + ROOM SPELL ALIGNMENT

Global rules:

- DO NOT add new spell mechanics
- DO NOT add new state systems
- DO NOT introduce new handlers unless strictly required for routing
- ALL migrated spells must use SpellRegistry, SpellEffectService, and StateService when mutation exists
- Legacy execution paths must FAIL CLOSED after migration

Migration checklist:

- `radiant_burst` — room-wide — registry-backed AoE routing through SpellEffectService and per-target StateService damage
- `shared_guard` — room-wide or group warding — registry-backed warding through SpellEffectService and StateService
- `glimmer` — utility — registry-backed utility effect through SpellEffectService and StateService
- `cleanse` — utility — registry-backed cleanse through SpellEffectService and StateService
- `hinder` — remaining legacy single-target debilitation — registry-backed through SpellEffectService and StateService
- `shielding` — remaining legacy self warding — registry-backed through SpellEffectService and StateService
- `radiant_aura` — deprecated unsupported legacy cyclic metadata — removed from execution and now fails closed as unregistered

Architecture audit:

- direct HP mutation in migrated spell paths: none outside StateService
- direct command spell logic in `cmd_prepare.py` and `cmd_cast.py`: none
- custom timers in migrated spell paths: none
- room authority writes in migrated spell paths: none