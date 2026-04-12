# Thief Profession — DireMud Extraction (v2.5)

## Source Data
- DireLore (primary)
- Elanthipedia (augmented)
- ShroomScripts Thief Secrets (supplemental external notes)

---

## Structured Output
```json
{
  "identity": {
    "role": "Survival-prime urban infiltrator and opportunistic striker built around stealth, theft, locks, traps, hidden travel, and concentration-driven khri rather than mana casting.",
    "strengths": [
      "Stealth-based scouting, stalking, and position control",
      "Pickpocketing, shoplifting, burglary, and mark-based target assessment",
      "Locksmithing, trap detection, trap disarming, and lockpick carving",
      "Burst damage and control from hiding via backstab, blindside, snipe, and ambushes",
      "Urban bonus, confidence bonus, and province-level reputation systems that reinforce thief play in cities",
      "Hidden infrastructure through passages, contacts, sign language, voice throw, and disguise-adjacent social concealment"
    ],
    "weaknesses": [
      "Reliant on hiding, positioning, and perception matchups rather than frontal durability",
      "Crime systems generate justice risk, wanted status, reputation loss, and higher contact costs",
      "Confidence can go negative and suppress effective ranks or negate urban advantage",
      "No mana use, no attunement, no targeted magic, no casting, and no cambrinth charging",
      "Repeated thefts against the same target or shop escalate rapidly and become failure-prone",
      "Structured DireLore support for full thief join flow and several non-khri verbs is sparse"
    ],
    "core_playstyle": "Operate from stealth, assess the target first, exploit urban terrain, use khri to sharpen contests, strike or steal on favorable odds, and disengage before heat or open confrontation collapses the advantage."
  },
  "skills": [
    {
      "name": "Stealth",
      "category": "core",
      "usage": "Hide, stalk, sneak, snipe setup, ambush setup, and general hidden movement.",
      "contested_by": ["Perception"],
      "used_for": ["hide", "stalk", "sneak", "snipe", "ambush positioning", "stealth defense"]
    },
    {
      "name": "Thievery",
      "category": "core",
      "usage": "Stealing coins, gems, shop items, burglary rewards, and slip maneuvers.",
      "contested_by": ["Perception", "shopkeeper attention", "justice response"],
      "used_for": ["steal", "shoplift", "pickpocket", "breaking and entering", "Slip"]
    },
    {
      "name": "Locksmithing",
      "category": "core",
      "usage": "Disarming traps, picking locks, carving lockpicks, and opening boxes safely.",
      "contested_by": ["trap and lock difficulty"],
      "used_for": ["disarm", "pick", "carve", "fix lockpick", "glance support"]
    },
    {
      "name": "Backstab",
      "category": "core",
      "usage": "High-value melee attacks and body-part ambush learning from stealth.",
      "contested_by": ["Perception", "combat defenses"],
      "used_for": ["backstab", "ambush targeting", "snipe modifier"]
    },
    {
      "name": "Perception",
      "category": "core",
      "usage": "Spotting hidden actors, defending against theft, reading traps, and improving mark training.",
      "contested_by": ["Stealth", "Thievery"],
      "used_for": ["anti-theft defense", "spot hidden", "mark", "trap work"]
    },
    {
      "name": "Evasion",
      "category": "core",
      "usage": "Defensive baseline for a light, mobile thief combat profile.",
      "contested_by": ["enemy offense"],
      "used_for": ["survival", "Elusion synergy", "combat mobility"]
    },
    {
      "name": "Athletics",
      "category": "core",
      "usage": "Movement support and part of the broader survival advancement burden.",
      "contested_by": [],
      "used_for": ["survival circling", "burglary support", "Khri Flight synergy"]
    },
    {
      "name": "Small Edged",
      "category": "secondary",
      "usage": "Recommended thief weapon class for backstabbing and close combat.",
      "contested_by": ["combat defenses"],
      "used_for": ["backstab", "Khri Eliminate", "general melee"]
    },
    {
      "name": "Brawling",
      "category": "secondary",
      "usage": "Supports ambush styles such as Clout and synergizes with some khri.",
      "contested_by": ["combat defenses"],
      "used_for": ["Ambush Clout", "Khri Elusion", "close combat"]
    },
    {
      "name": "Bow",
      "category": "secondary",
      "usage": "Hidden ranged attacks and thief access to snipe with aimable missile weapons.",
      "contested_by": ["Perception", "combat defenses"],
      "used_for": ["snipe", "hidden ranged combat"]
    },
    {
      "name": "Crossbow",
      "category": "secondary",
      "usage": "Alternative aimable ranged weapon for hidden attacks and snipe.",
      "contested_by": ["Perception", "combat defenses"],
      "used_for": ["snipe", "hidden ranged combat"]
    },
    {
      "name": "Light Thrown",
      "category": "secondary",
      "usage": "Useful for dirt-based ambush play and thrown weapon coverage.",
      "contested_by": ["combat defenses"],
      "used_for": ["ambush support", "thrown combat"]
    },
    {
      "name": "Parry Ability",
      "category": "secondary",
      "usage": "Required guild combat competency alongside two weapon classes.",
      "contested_by": ["enemy weapon attacks"],
      "used_for": ["survival in melee", "circle advancement"]
    },
    {
      "name": "Appraisal",
      "category": "secondary",
      "usage": "Improves target reading and is directly trained by Mark.",
      "contested_by": [],
      "used_for": ["mark", "shop theft assessment", "value reading"]
    },
    {
      "name": "Tactics",
      "category": "secondary",
      "usage": "Recommended lore choice and explicitly buffed or debuffed by khri.",
      "contested_by": [],
      "used_for": ["circle advancement", "Khri Cunning", "Khri Prowess"]
    },
    {
      "name": "Scholarship",
      "category": "secondary",
      "usage": "Recommended lore skill, supports scroll identification, and gates Slip teaching.",
      "contested_by": [],
      "used_for": ["Slip teaching", "scroll identification", "circle advancement"]
    },
    {
      "name": "Engineering",
      "category": "secondary",
      "usage": "Crafting support skill with free thief carving technique slots and khri synergy.",
      "contested_by": [],
      "used_for": ["lockpick carving", "Khri Muse", "crafting"]
    },
    {
      "name": "Alchemy",
      "category": "secondary",
      "usage": "Supports poison-oriented thief crafting and khri synergy.",
      "contested_by": [],
      "used_for": ["poison crafting", "Khri Muse", "crafting"]
    },
    {
      "name": "Light Armor",
      "category": "tertiary",
      "usage": "Preferred armor path because it minimizes stealth hindrance while preserving protection.",
      "contested_by": ["armor hindrance"],
      "used_for": ["defense", "low hindrance stealth play"]
    },
    {
      "name": "Inner Magic",
      "category": "tertiary",
      "usage": "Baseline supernatural support for starting and sustaining khri.",
      "contested_by": [],
      "used_for": ["Khri startup", "Khri stacking"]
    },
    {
      "name": "Augmentation",
      "category": "tertiary",
      "usage": "Supports augmentation-style khri and thief supernatural progression.",
      "contested_by": [],
      "used_for": ["Khri scaling"]
    },
    {
      "name": "Debilitation",
      "category": "tertiary",
      "usage": "Trained through thief ambushes and debilitative khri contests.",
      "contested_by": ["target defenses or stats"],
      "used_for": ["ambushes", "control khri"]
    },
    {
      "name": "Utility",
      "category": "tertiary",
      "usage": "Supports non-damaging khri and stealth-support supernatural effects.",
      "contested_by": [],
      "used_for": ["Khri Hasten", "Khri Dampen", "Khri Vanish"]
    },
    {
      "name": "Warding",
      "category": "tertiary",
      "usage": "Supports protective khri such as Adaptation, Serenity, and Sagacity.",
      "contested_by": [],
      "used_for": ["defensive khri"]
    },
    {
      "name": "Arcana",
      "category": "tertiary",
      "usage": "Limited magical-device interaction; useful but not part of true mana casting.",
      "contested_by": [],
      "used_for": ["crystal interaction", "magical device efficiency"]
    }
  ],
  "abilities": [
    {
      "ability": "Hide",
      "type": "stealth",
      "requires": ["Stealth ranks", "concealable environment"],
      "contests": ["Perception"],
      "failure_states": ["You are spotted while hiding", "Wounds, armor hindrance, combat status, and proximity increase difficulty"],
      "success_states": ["You become hidden", "Enables backstab, ambush, snipe, safer theft"],
      "risk_level": "medium"
    },
    {
      "ability": "Stalk",
      "type": "stealth",
      "requires": ["Hidden state", "Stealth ranks", "target to follow"],
      "contests": ["Perception"],
      "failure_states": ["Target notices you", "Closer combat distance adds strong spotting bonuses"],
      "success_states": ["Maintain hidden tracking position on a target", "Trains Stealth"],
      "risk_level": "medium"
    },
    {
      "ability": "Sneak",
      "type": "stealth",
      "requires": ["Stealth ranks", "hidden movement route"],
      "contests": ["Perception"],
      "failure_states": ["Movement reveals you"],
      "success_states": ["Room-to-room movement while trying to remain unseen"],
      "risk_level": "medium"
    },
    {
      "ability": "Steal",
      "type": "crime",
      "requires": ["Thievery ranks", "valid NPC, PC, shop, or special target"],
      "contests": ["Perception", "shopkeeper attention", "justice systems"],
      "failure_states": ["Critical failure or detection", "Justice charges", "PvP-open if stealing from PCs", "Increased target/shop attention"],
      "success_states": ["Acquire coins, gems, or items", "Train Thievery"],
      "risk_level": "high"
    },
    {
      "ability": "Mark",
      "type": "utility",
      "requires": ["Thief-only access", "Appraisal", "Perception"],
      "contests": ["Effective ranks vs target skill spread"],
      "failure_states": ["Low certainty on result", "Too many shop marks can trigger hooliganism attention"],
      "success_states": ["Assesses stealing, stalking, hiding, backstab, and general odds", "Reads wealth and coin volume", "Trains Appraisal and Perception"],
      "risk_level": "low"
    },
    {
      "ability": "Backstab",
      "type": "combat",
      "requires": ["Hidden state", "Small edged thrusting weapon under 30 stones", "upright target or body-part targeting"],
      "contests": ["Perception", "combat defenses"],
      "failure_states": ["Target notices the attack", "Invalid weapon or target posture"],
      "success_states": ["Large damage and accuracy spike from stealth"],
      "risk_level": "high"
    },
    {
      "ability": "Blindside",
      "type": "combat",
      "requires": ["Hidden state", "melee range", "melee weapon"],
      "contests": ["combat defenses"],
      "failure_states": ["Loses hidden advantage if setup collapses"],
      "success_states": ["Far more damage than a simple ambush or normal weapon attack"],
      "risk_level": "high"
    },
    {
      "ability": "Snipe",
      "type": "combat",
      "requires": ["40th circle", "Survival-prime guild status", "Bow, Crossbow, or Sling", "hidden state"],
      "contests": ["Perception", "combat defenses"],
      "failure_states": ["Shot becomes normal attack", "You are pulled from hiding", "Invisibility alone always breaks"],
      "success_states": ["Attack from hiding while remaining hidden", "Accuracy bonus", "Only target sees attacker name on success"],
      "risk_level": "high"
    },
    {
      "ability": "Pick",
      "type": "utility",
      "requires": ["Locksmithing", "lockpick", "locked target"],
      "contests": ["lock difficulty"],
      "failure_states": ["Failed opening attempt", "Lockpick break or wasted time on hard locks"],
      "success_states": ["Lock opened", "Trains Locksmithing"],
      "risk_level": "medium"
    },
    {
      "ability": "Disarm",
      "type": "utility",
      "requires": ["Locksmithing", "trapped box or mechanism"],
      "contests": ["trap difficulty"],
      "failure_states": ["Trap fires", "Quick or blind caution increases danger"],
      "success_states": ["Trap neutralized", "Can analyze or harvest trap parts", "Trains Locksmithing and some Perception"],
      "risk_level": "high"
    },
    {
      "ability": "Glance",
      "type": "utility",
      "requires": ["100 ranks in Lockpicking", "loot box target"],
      "contests": [],
      "failure_states": ["Insufficient skill yields no advanced read"],
      "success_states": ["See remaining trap count and lock count with more detail"],
      "risk_level": "low"
    },
    {
      "ability": "Lockpick Carving",
      "type": "utility",
      "requires": ["12th circle", "Locksmithing", "keyblank", "knife"],
      "contests": ["quality scales with Lockpicking and Agility"],
      "failure_states": ["Low-quality or failed pick creation"],
      "success_states": ["Create a usable lockpick", "Supports self-sufficient infiltration loops"],
      "risk_level": "low"
    },
    {
      "ability": "Slip",
      "type": "utility",
      "requires": ["Slip teaching", "circle gating", "Stealth and Thievery"],
      "contests": ["varies by maneuver"],
      "failure_states": ["Maneuver fails or reveals intent"],
      "success_states": ["Coin sleights, object transfer, worn-item manipulation, hide+stalk pairing, hide+sneak pairing, ground-item acquisition"],
      "risk_level": "medium"
    },
    {
      "ability": "Contacts",
      "type": "utility",
      "requires": ["Thief guild status", "available contact slots by circle", "coins to pay the contact"],
      "contests": [],
      "failure_states": ["High heat raises fees", "Low slot count limits simultaneous use"],
      "success_states": ["Locate people, route errands, and offload city-side utility work"],
      "risk_level": "low"
    },
    {
      "ability": "Passages",
      "type": "stealth",
      "requires": ["Thief access to known passage network"],
      "contests": [],
      "failure_states": ["Unknown route or unavailable local passage"],
      "success_states": ["Use hidden shortcuts and bolt-holes across thief cities"],
      "risk_level": "low"
    },
    {
      "ability": "Sign Language",
      "type": "utility",
      "requires": ["Thief-only training"],
      "contests": ["Perception"],
      "failure_states": ["Non-thieves with enough perception notice the hand motions"],
      "success_states": ["Covert guild communication"],
      "risk_level": "low"
    },
    {
      "ability": "Voice Throw",
      "type": "utility",
      "requires": ["teaching from a real Bard", "sufficient thief level and skill"],
      "contests": [],
      "failure_states": ["Guild-disfavored overt pursuit can bring attention"],
      "success_states": ["Project voice in deceptive ways for misdirection"],
      "risk_level": "medium"
    },
    {
      "ability": "SMIRK SELF",
      "type": "utility",
      "requires": ["Thief access"],
      "contests": [],
      "failure_states": [],
      "success_states": ["Reports current confidence and urban bonus state"],
      "risk_level": "low"
    },
    {
      "ability": "Poison Resistance",
      "type": "utility",
      "requires": ["additional guild trust and poison training"],
      "contests": [],
      "failure_states": ["Does not make the thief poison-proof"],
      "success_states": ["Passive resistance to poison threats"],
      "risk_level": "low"
    },
    {
      "ability": "Pretend Guild",
      "type": "utility",
      "requires": ["Thief roleplay choice and guild access"],
      "contests": [],
      "failure_states": ["Poor use can draw heat to the guild"],
      "success_states": ["Conceals true guild affiliation for social cover"],
      "risk_level": "medium"
    },
    {
      "ability": "Ambush Choke",
      "type": "combat",
      "requires": ["3rd circle", "hiding", "melee range", "ambush slot"],
      "contests": ["Target debilitation resistance"],
      "failure_states": ["Control effect fails or weakens"],
      "success_states": ["Reduces stamina and causes fatigue damage"],
      "risk_level": "high"
    },
    {
      "ability": "Ambush Screen",
      "type": "combat",
      "requires": ["30th circle", "Ambush Choke", "hiding", "melee range", "ambush slot"],
      "contests": ["Target debilitation resistance"],
      "failure_states": ["Perception debuff and roundtime pulse fail to land"],
      "success_states": ["Reduces Perception and can add random roundtimes to engaged targets"],
      "risk_level": "high"
    },
    {
      "ability": "Ambush Slash",
      "type": "combat",
      "requires": ["39th circle", "hiding", "melee range", "ambush slot"],
      "contests": ["Target debilitation resistance"],
      "failure_states": ["Movement denial fails"],
      "success_states": ["Prevents retreat or movement briefly and may drop the target to knees"],
      "risk_level": "high"
    },
    {
      "ability": "Ambush Stun",
      "type": "combat",
      "requires": ["25th circle", "hiding", "melee range", "ambush slot"],
      "contests": ["Target debilitation resistance"],
      "failure_states": ["Stun fails or shortens"],
      "success_states": ["Head damage and variable stun duration"],
      "risk_level": "high"
    },
    {
      "ability": "Ambush Clout",
      "type": "combat",
      "requires": ["50th circle", "Ambush Stun", "hiding", "melee range", "ambush slot"],
      "contests": ["Target debilitation resistance"],
      "failure_states": ["Concentration-pressure play fails"],
      "success_states": ["Concentration damage, pulsing drain, and can strip prepared spells"],
      "risk_level": "high"
    },
    {
      "ability": "Ambush Ignite",
      "type": "combat",
      "requires": ["Ambush Slash", "hiding", "melee range", "ambush slot"],
      "contests": ["Target defenses"],
      "failure_states": ["Armor damage or body damage effect fails"],
      "success_states": ["Damages armor or applies physical damage to unarmored areas"],
      "risk_level": "high"
    },
    {
      "ability": "Khri Darken",
      "type": "stealth",
      "requires": ["Khri access", "Concentration", "1 slot"],
      "contests": [],
      "failure_states": ["Startup can fail under poor confidence or weak supernatural support", "Ends when concentration runs out or duration expires"],
      "success_states": ["Boosts Stealth"],
      "risk_level": "low"
    },
    {
      "ability": "Khri Hasten",
      "type": "utility",
      "requires": ["Khri access", "Concentration", "1 slot"],
      "contests": [],
      "failure_states": ["Can drop when concentration is exhausted"],
      "success_states": ["Reduces roundtime for melee, thrown attacks, disarming, picking, and some armor actions"],
      "risk_level": "low"
    },
    {
      "ability": "Khri Plunder",
      "type": "crime",
      "requires": ["Hasten", "Concentration", "2 slots"],
      "contests": [],
      "failure_states": ["Cannot be maintained if concentration collapses"],
      "success_states": ["Boosts Thievery and Discipline"],
      "risk_level": "medium"
    },
    {
      "ability": "Khri Safe",
      "type": "utility",
      "requires": ["Hasten", "14th circle", "Concentration", "2 slots"],
      "contests": [],
      "failure_states": ["Trap-dodge support may not save bad locksmithing decisions"],
      "success_states": ["Boosts Locksmithing and can dodge a blown trap while opening boxes"],
      "risk_level": "medium"
    },
    {
      "ability": "Khri Slight",
      "type": "crime",
      "requires": ["Plunder", "Concentration", "2 slots"],
      "contests": [],
      "failure_states": ["Does not remove all criminal risk outside shop contexts"],
      "success_states": ["Reduces chance of being caught shoplifting, potentially to zero"],
      "risk_level": "medium"
    },
    {
      "ability": "Khri Strike",
      "type": "combat",
      "requires": ["Darken", "13th circle", "Concentration", "3 slots"],
      "contests": [],
      "failure_states": ["Held-weapon requirement limits benefit"],
      "success_states": ["Boosts Backstab and many held weapon skills"],
      "risk_level": "medium"
    },
    {
      "ability": "Khri Terrify",
      "type": "combat",
      "requires": ["Focus", "Concentration", "2 slots"],
      "contests": ["Target debilitation resistance"],
      "failure_states": ["Immobilize fails or is resisted"],
      "success_states": ["Single-target immobilize"],
      "risk_level": "high"
    },
    {
      "ability": "Khri Silence",
      "type": "stealth",
      "requires": ["Darken", "Concentration", "2 slots"],
      "contests": [],
      "failure_states": ["Pulsing invisibility ends when concentration fails"],
      "success_states": ["Provides pulsing invisibility support"],
      "risk_level": "medium"
    },
    {
      "ability": "Khri Shadowstep",
      "type": "stealth",
      "requires": ["Dampen", "Concentration", "2 slots"],
      "contests": [],
      "failure_states": ["Concentration-intensive upkeep"],
      "success_states": ["Decreases advance time while hidden and can allow 0 RT sneaking in town"],
      "risk_level": "medium"
    },
    {
      "ability": "Khri Vanish",
      "type": "stealth",
      "requires": ["Silence", "40th circle", "Concentration", "2 slots"],
      "contests": [],
      "failure_states": ["High startup cost"],
      "success_states": ["Instant invisibility and retreat"],
      "risk_level": "high"
    },
    {
      "ability": "Khri Dampen",
      "type": "stealth",
      "requires": ["Darken", "Concentration", "2 slots"],
      "contests": [],
      "failure_states": ["Utility protection falls off with concentration loss"],
      "success_states": ["Reduces stealth hindrance, blocks hunt, and adds anti-locate protection"],
      "risk_level": "low"
    },
    {
      "ability": "Khri Focus",
      "type": "utility",
      "requires": ["Khri access", "Concentration", "1 slot"],
      "contests": [],
      "failure_states": ["May be harder to start at low confidence"],
      "success_states": ["Boosts Agility"],
      "risk_level": "low"
    },
    {
      "ability": "Khri Sight",
      "type": "utility",
      "requires": ["Focus", "14th circle", "Concentration", "1 slot"],
      "contests": [],
      "failure_states": ["Requires enough supernatural capacity to sustain"],
      "success_states": ["Boosts Perception and grants darkvision"],
      "risk_level": "low"
    },
    {
      "ability": "Khri Sensing",
      "type": "utility",
      "requires": ["Dampen", "Concentration", "3 slots"],
      "contests": [],
      "failure_states": ["Remote-view utility ends with concentration loss"],
      "success_states": ["Remote view into a neighboring room and passive spot on hidden targets"],
      "risk_level": "medium"
    },
    {
      "ability": "Khri Prowess",
      "type": "combat",
      "requires": ["Focus", "14th circle", "Concentration", "2 slots"],
      "contests": ["Target defenses/stat contests"],
      "failure_states": ["PvP and PvE effects split by context"],
      "success_states": ["Reduces tactics, reflex, and either OF or tactics depending on context"],
      "risk_level": "high"
    },
    {
      "ability": "Khri Eliminate",
      "type": "combat",
      "requires": ["Prowess", "60th circle", "Small Edged weapon", "Concentration", "2 slots"],
      "contests": ["offensive resolution after activation"],
      "failure_states": ["Short window and high one-time cost"],
      "success_states": ["Small edged attacks ignore armor and shield briefly"],
      "risk_level": "high"
    }
  ],
  "systems": {
    "stealth": {
      "entry_conditions": [
        "Stealth is contested against Perception",
        "Hiding, stalking, and hidden movement all depend on Stealth",
        "Armor type, wounds, combat status, and Discipline affect success",
        "Urban bonus and positive confidence improve contested effective ranks for many thief actions",
        "Hidden setup strongly improves backstab, ambush, snipe, and some theft patterns"
      ],
      "break_conditions": [
        "Failing the Perception contest while hiding or stalking",
        "Speaking while hidden can trigger a room-wide stealth check and reveal identity details on failure",
        "Failing Snipe or using only invisibility without actual hiding reveals the attacker",
        "Entering closer combat engagement makes hiding significantly harder",
        "Concentration failure ends supporting khri"
      ],
      "detection_rules": [
        "Perception is the primary anti-stealth and anti-theft defense",
        "Characters who do not notice the hide can still SEARCH for the hidden actor",
        "Mark uses effective ranks and can assess hiding, stalking, stealing, and backstab odds",
        "Stealth training includes hide, stalk, sneak, snipe, ambush, and advancing on a target while hidden"
      ],
      "modifiers": [
        "Urban bonus cannot go negative and ranges from neutral to positive",
        "Low confidence hinders base ranks by roughly 5% and can negate urban advantage",
        "Only stealth, blindside, and thievery currently modify thief confidence according to the augmented page",
        "Thieves eventually avoid the extra hidden-loading penalty other guilds pay with ranged weapons"
      ],
      "khri_suite": [
        "Khri Darken",
        "Khri Dampen",
        "Khri Silence",
        "Khri Shadowstep",
        "Khri Vanish",
        "Khri Sight",
        "Khri Sensing"
      ]
    },
    "crime": {
      "actions": [
        "Steal from NPCs",
        "Steal from players",
        "Shoplift from stores",
        "Use Breaking and Entering / BURGLE for property theft",
        "Mark targets and items before theft",
        "Use Slip maneuvers for stealthy transfers and hidden movement pairings"
      ],
      "detection": [
        "Perception defends against player theft",
        "Shopkeepers track attention / heat and become harder to beat after theft",
        "Repeated NPC thefts trigger a 15-minute caught-likely timer on that NPC",
        "Repeated steals from the same player within an hour become nearly guaranteed failure",
        "Stealing from PCs has an approach timer unless bypassed by certain thief tech"
      ],
      "consequences": [
        "Stealing from PCs locks the thief PvP-open for 4 hours",
        "NPC theft and shop theft are justice offenses",
        "Pickpocketing is lighter than pilfering from shops or felony stealing from PCs",
        "Caught crimes lower province reputation",
        "Very low reputation can cause the guild to kill the thief on guild entry"
      ],
      "escalation": [
        "Shop heat persists about one hour after a theft",
        "More recent crime and warrants make contacts more expensive",
        "Guild reputation is restored with stolen-good donations, TASKs, and staying not-wanted",
        "Marking too many shop items can itself trigger unwanted shopkeeper notice and hooliganism risk"
      ]
    },
    "infiltration": {
      "lockpicking": {
        "flow": [
          "PICK ANALYZE to identify lock type",
          "PICK IDENTIFY to appraise difficulty against your current skill",
          "PICK with caution level CAREFUL / default / QUICK / BLIND",
          "Use or carve higher-quality lockpicks as skill rises"
        ],
        "modifiers": [
          "Armor hindrance matters, especially on hands",
          "Agility and Reflex help the actual pick/disarm action",
          "Mentals matter primarily for IDENTIFY-style reads",
          "Kneeling or sitting improves success odds",
          "Khri Hasten and Khri Safe directly support locksmithing loops"
        ],
        "failure_profile": [
          "Higher-difficulty locks become longshots or effectively impossible",
          "Wrong caution level raises failure cost",
          "Bad tool quality reduces reliability"
        ]
      },
      "traps": {
        "flow": [
          "DISARM IDENTIFY to learn trap type and relative danger",
          "DISARM with chosen caution level",
          "DISARM ANALYZE to inspect harvestable parts",
          "DISARM HARVEST to recover a mechanism piece"
        ],
        "modifiers": [
          "Trap difficulty uses a 1-17 style appraisal ladder",
          "Khri Safe can help dodge blown traps",
          "Khri Hasten improves roundtime on disarm loops"
        ],
        "failure_profile": [
          "Quick and blind speeds are faster but more dangerous",
          "Failed disarm can trigger the trap directly",
          "Trap work is one of the sharper risk-reward skill loops in the profession"
        ]
      },
      "burglary": {
        "summary": "Breaking and Entering is one of the best Thievery training loops from 0 ranks upward, but it carries substantial legal and operational risk and also trains Locksmithing, Athletics, and Stealth depending on tools and methods."
      }
    },
    "combat": {
      "style": "Stealth-first combat uses hidden positioning to convert information advantage into burst damage, debuffs, immobilization, or clean disengage windows rather than standing toe-to-toe for attrition.",
      "positioning_requirements": [
        "Backstab and Blindside want hiding and melee range",
        "Snipe wants hiding plus an aimable ranged weapon",
        "Thief ambushes usually want hiding, melee range, and often a physical component such as dirt or a weapon",
        "Some targets are invalid or less efficient for pure backstab, pushing the thief toward body-part ambushes instead"
      ],
      "advantages_from_stealth": [
        "Hidden attacks gain accuracy and/or damage advantage",
        "Successful Snipe keeps room anonymity except to the target",
        "Backstab and Blindside convert stealth into burst lethality",
        "Khri suite amplifies stealth, weapon, and control output before the strike"
      ],
      "guild_only_ambush_moves": [
        "Ambush Choke",
        "Ambush Screen",
        "Ambush Slash",
        "Ambush Stun",
        "Ambush Clout",
        "Ambush Ignite"
      ],
      "notable_combat_support": [
        "Khri Strike",
        "Khri Prowess",
        "Khri Eliminate",
        "Khri Steady",
        "Khri Flight",
        "Khri Terrify"
      ]
    }
  },
  "progression": {
    "circle_model": {
      "primary_pressure": "Circle advancement is heavily Survival-driven, with Stealth and Thievery as soft requirements and a minimum of eight viable Survival skills needed to circle reliably.",
      "secondary_pressure": "Maintain two weapon classes plus Parry, three Lore skills, one Armor skill, and enough Supernatural/Magic support to keep khri online.",
      "confirmed_structure": {
        "primary_skillset": "Survival",
        "secondary_skillsets": ["Weapon", "Lore"],
        "tertiary_skillsets": ["Armor", "Magic"]
      }
    },
    "training_loops": [
      "Hide / stalk / sneak in combat and around valid observers",
      "Backstab or ambush from hiding for stealth plus offensive growth",
      "Use Mark on hard targets or shop items to train Appraisal and Perception",
      "Shoplift progressively harder goods while respecting one-hour shop heat",
      "Steal from NPCs on rotation and avoid their local reset timers",
      "Break into properties with BURGLE for high-risk Thievery growth",
      "Disarm and pick creature boxes, then carve or fix your own lockpicks",
      "Keep khri active and use debilitative ambushes to train Supernatural skills"
    ],
    "optimal_training_loops": [
      "Early: hide against passive observers, easy shops, easy NPC theft, low-end boxes",
      "Mid: combat hiding plus backstab/ambush, rotational shop theft, burglary, box pipelines",
      "Late: stacked khri, harder burglary and shoplifting, snipe, ambush chains, reputation-aware contact and passage routing"
    ],
    "risk_vs_reward_scaling": [
      "Breaking and Entering teaches extremely well but comes with major operational risk",
      "Shoplifting teaches well but repeated hits on the same shop sharply worsen odds",
      "Player theft is mechanically possible but poor for training and carries PvP-open consequences",
      "Lock/trap work scales strongly with difficulty, caution choice, tool quality, and khri support",
      "Urban bonus and confidence create a thief-specific reward loop for succeeding at risky thief actions"
    ]
  },
  "pvp": {
    "interaction_model": "Thieves pressure players through stealth contests, approach windows, theft, backstab, blindside, and hidden ranged attacks rather than open attrition alone.",
    "counterplay_systems": [
      "Perception is the primary defense against theft and many stealth actions",
      "Approach timers and repeat-theft pressure limit repeated PC stealing",
      "Open containers and gem handling create theft-specific vulnerability rules",
      "Target awareness can nullify hide/stalk/backstab plans",
      "PvP-open status after PC theft creates a strong deterrent and retaliation window"
    ],
    "detection_vs_stealth_dynamics": [
      "Mark can estimate player-specific hide, stalk, backstab, and stealing odds",
      "Effective-rank changes from khri, confidence, urban bonus, wounds, and hindrance all matter",
      "Some anti-theft workarounds exist, such as open gem pouches with junk gems to alter steal targeting"
    ],
    "notable_risks": [
      "PC theft is high-visibility behavior mechanically and socially",
      "Backstab or snipe failure turns the fight into normal open combat",
      "Thief strengths fade sharply when the hidden approach is lost"
    ]
  },
  "npc_interactions": {
    "guard_reactions": [
      "Justice zones treat stealing and related conduct as criminal offenses",
      "Being caught raises province heat and can produce wanted status",
      "Staying wanted damages reputation and downstream guild support"
    ],
    "shopkeeper_behavior": [
      "Shopkeepers keep closer watch for about one hour after a theft in that shop",
      "Marking too many items can draw unwanted shopkeeper notice before the theft even starts",
      "Harder items teach more but also carry worse grab and getaway odds"
    ],
    "faction_consequences": [
      "Reputation is province-sensitive and reflects how thief leadership currently views the member",
      "Low reputation can lock access to thief support or even cause lethal guild punishment",
      "Contact fees rise with local heat and warrants",
      "Reputation recovery comes from stolen-goods donations, guild TASKs, and staying clear of law attention"
    ],
    "guild_infrastructure": [
      "Passages provide safe movement and bolt-holes",
      "Contacts scale by circle at one extra contact per 20 circles up to five",
      "Guild halls and join routes are intentionally secretive rather than public onboarding spaces"
    ]
  },
  "gaps": {
    "missing_in_direlore": [
      "No thief rows exist in profession_abilities despite the profession having a large command surface",
      "The promoted Thief entity has no useful fact rows for mechanics, join flow, or advancement behavior",
      "There is no clean normalized guild join-flow record for thief secrecy tests, Crossing street joiner behavior, or Riverhaven test routing",
      "No normalized province reputation table exists for thief reputation states, thresholds, or punishments",
      "No normalized slip progression table exists even though the page contains level unlocks",
      "No normalized contact action table exists for contact task types or fee rules",
      "No normalized passage graph exists for thief-only travel infrastructure",
      "No normalized reduced-load-while-hidden rule exists in mechanic tables",
      "No normalized poison-resistance progression or exact trigger rules were found"
    ],
    "incomplete_structures": [
      "canon_professions captures only a short summary and skillset shell for Thief",
      "profession_skills stores only skillset categories, not the actual named thief training skills",
      "canon_abilities covers many khri and ambushes but does not cover Mark, Slip, Contacts, Passages, Sign Language, Glance, Poison Resistance, or Pretend Guild as first-class ability rows",
      "confidence and urban bonus are preserved mainly in raw page text rather than rule tables",
      "crime heat, shopkeeper attention, and PvP-open consequences are present as prose but not normalized as mechanic rules"
    ],
    "recommended_schema_additions": [
      "guild_join_flows",
      "profession_verbs",
      "profession_system_modifiers",
      "guild_reputation_rules",
      "contact_actions",
      "passage_networks",
      "theft_consequence_rules",
      "skill_role_mappings"
    ]
  },
  "schema_recommendations": [
    {
      "field": "profession_verbs",
      "suggested_schema": "profession_verbs(profession_id, verb_name, verb_type, min_circle, trains_skills[], prerequisites[], contests[], justice_risk, pvp_risk, source_url, confidence)",
      "reason": "Thief mechanics are currently spread across raw sections and missing entirely from profession_abilities for most verbs."
    },
    {
      "field": "guild_join_flows",
      "suggested_schema": "guild_join_flows(profession_id, province, secrecy_level, prerequisites_json, entry_hint, join_npc, join_steps_json, source_url, confidence)",
      "reason": "Thief joining is explicitly secrecy-based and province-specific, but there is no normalized storage for that onboarding path."
    },
    {
      "field": "guild_reputation_rules",
      "suggested_schema": "guild_reputation_rules(profession_id, province, reputation_band, access_effects[], punishment_effects[], recovery_actions[], source_url, confidence)",
      "reason": "Reputation directly affects access, support, and even death punishment, but is only preserved as prose."
    },
    {
      "field": "profession_system_modifiers",
      "suggested_schema": "profession_system_modifiers(profession_id, system_name, modifier_name, affected_skills[], numeric_range, trigger_conditions_json, source_url, confidence)",
      "reason": "Urban bonus and confidence are central thief mechanics with cross-system impact and should not remain raw-text only."
    },
    {
      "field": "contact_actions",
      "suggested_schema": "contact_actions(profession_id, action_name, min_circle, slot_cost, fee_formula_text, heat_modifier_text, target_scope, source_url, confidence)",
      "reason": "Contacts are operationally important but current storage does not say what tasks they can perform or how fees scale."
    },
    {
      "field": "passage_networks",
      "suggested_schema": "passage_networks(region, node_name, node_type, connected_to[], access_requirements_json, source_url, confidence)",
      "reason": "Passages are a major thief mobility system and currently remain descriptive only."
    },
    {
      "field": "theft_consequence_rules",
      "suggested_schema": "theft_consequence_rules(action_type, target_type, timer_rule, heat_rule, justice_charge, pvp_effect, repeat_penalty_text, source_url, confidence)",
      "reason": "Shop heat, NPC reset timers, PC PvP-open, and repeat-theft penalties are engineering-relevant rules hidden in prose."
    },
    {
      "field": "skill_role_mappings",
      "suggested_schema": "skill_role_mappings(profession_id, skill_name, tier, role_label, recommended_for[], source_url, confidence)",
      "reason": "profession_skills currently stores only coarse skillset categories and not the named skill matrix players actually train."
    }
  ]
}
```

## Gap Analysis
```json
{
  "missing_in_direlore": [
    "No thief rows exist in profession_abilities despite the profession having a large command surface.",
    "The promoted Thief entity has no useful fact rows for mechanics, join flow, or advancement behavior.",
    "No normalized guild-join flow captures the secrecy-based thief induction, Crossing street joiner, or Riverhaven test.",
    "No normalized reputation-state model captures province bands, access effects, or lethal guild punishment.",
    "No normalized contact task model captures what contacts can do, their fees, or heat scaling.",
    "No normalized passage network model captures thief-only travel routes and access points.",
    "No normalized rule row captures reduced ranged-load penalty while hidden.",
    "No normalized rule row captures poison resistance progression or exact defensive behavior."
  ],
  "incomplete_structures": [
    "canon_professions is summary-level only.",
    "profession_skills stores only broad skillsets, not named thief training skills.",
    "canon_abilities covers much of khri and ambushes but not the full thief verb suite.",
    "Confidence, urban bonus, shop heat, and some PvP theft rules remain prose-backed rather than fully normalized."
  ],
  "recommended_schema_additions": [
    "guild_join_flows",
    "profession_verbs",
    "profession_system_modifiers",
    "guild_reputation_rules",
    "contact_actions",
    "passage_networks",
    "theft_consequence_rules",
    "skill_role_mappings"
  ]
}
```

## Schema Recommendations
```json
[
  {
    "field": "profession_verbs",
    "suggested_schema": "profession_verbs(profession_id, verb_name, verb_type, min_circle, trains_skills[], prerequisites[], contests[], justice_risk, pvp_risk, source_url, confidence)",
    "reason": "Thief mechanics are currently spread across raw sections and missing entirely from profession_abilities for most verbs."
  },
  {
    "field": "guild_join_flows",
    "suggested_schema": "guild_join_flows(profession_id, province, secrecy_level, prerequisites_json, entry_hint, join_npc, join_steps_json, source_url, confidence)",
    "reason": "Thief joining is explicitly secrecy-based and province-specific, but there is no normalized storage for that onboarding path."
  },
  {
    "field": "guild_reputation_rules",
    "suggested_schema": "guild_reputation_rules(profession_id, province, reputation_band, access_effects[], punishment_effects[], recovery_actions[], source_url, confidence)",
    "reason": "Reputation directly affects access, support, and even death punishment, but is only preserved as prose."
  },
  {
    "field": "profession_system_modifiers",
    "suggested_schema": "profession_system_modifiers(profession_id, system_name, modifier_name, affected_skills[], numeric_range, trigger_conditions_json, source_url, confidence)",
    "reason": "Urban bonus and confidence are central thief mechanics with cross-system impact and should not remain raw-text only."
  },
  {
    "field": "contact_actions",
    "suggested_schema": "contact_actions(profession_id, action_name, min_circle, slot_cost, fee_formula_text, heat_modifier_text, target_scope, source_url, confidence)",
    "reason": "Contacts are operationally important but current storage does not say what tasks they can perform or how fees scale."
  },
  {
    "field": "passage_networks",
    "suggested_schema": "passage_networks(region, node_name, node_type, connected_to[], access_requirements_json, source_url, confidence)",
    "reason": "Passages are a major thief mobility system and currently remain descriptive only."
  },
  {
    "field": "theft_consequence_rules",
    "suggested_schema": "theft_consequence_rules(action_type, target_type, timer_rule, heat_rule, justice_charge, pvp_effect, repeat_penalty_text, source_url, confidence)",
    "reason": "Shop heat, NPC reset timers, PC PvP-open, and repeat-theft penalties are engineering-relevant rules hidden in prose."
  },
  {
    "field": "skill_role_mappings",
    "suggested_schema": "skill_role_mappings(profession_id, skill_name, tier, role_label, recommended_for[], source_url, confidence)",
    "reason": "profession_skills currently stores only coarse skillset categories and not the named skill matrix players actually train."
  }
]
```

---

## ShroomScripts Supplemental Extraction

Source:
- https://sites.google.com/site/shroomscripts/thief-secrets

Confidence note:
- Treat this as supplemental player-facing guidance rather than a replacement for DireLore or canon tables.
- It is most useful for join flow details, practical guild access notes, slip progression, and operational thief bonus guidance.

### Join Flow And Guild Access
- Crossing join route is described as: find the blind beggar, `ASK BEGGAR ABOUT THIEVES`, `ASK BEGGAR ABOUT JOIN` twice, steal water from the alchemist shop, give it to the beggar, then ask about skill/train for early thief guidance.
- Crossing join note: the water must be stolen from the alchemist shop; buying it or sourcing it elsewhere does not complete the guild entry step.
- Crossing join note: the page claims you must not belong to another guild when attempting the beggar route.
- Riverhaven note: the page claims guild joining from Riverhaven no longer appears available.
- Crossing guild access notes include multiple entrances, including the Raven's Court slitted door via `TAP KNOCKER`, plus passage-linked entrances for thieves who already know Passages.
- Riverhaven access notes describe multiple password-gated entrances and indicate the password comes from asking Jackwater.
- Shard access notes describe a Malik pawnshop quest to obtain the password, with shiny apple / etrana flower / basket retrieval options.
- Muspar'i access notes describe Ershhn escorting thieves into the guild outpost through a forced transport sequence into Kings' Hidden Passage.

### Slip Teaching And Progression
- `SLIP TEACH <target>` is described as the teaching method.
- The page claims the teacher needs at least `100` Teaching skill to instruct Slip.
- The page claims the student does not need Scholarship to learn Slip.
- The page claims there is no circle requirement to be taught the Slip basics.
- The page claims Slip only needs to be taught once; subsequent Slip abilities unlock automatically by circle.
- Slip is described here as using a combination of Stealing and Stalking skill, while ability accumulation is circle-based.

### Slip Circle Unlocks
- Circle 10: sleight of hand with coins.
- Circle 15: slip coins to other people.
- Circle 20: slip personal objects to and from personal containers.
- Circle 30: slip personal objects to another person's containers or hands.
- Circle 40: slip worn items on and off.
- Circle 50: slip into hiding and stalk at the same time.
- Circle 60: slip into hiding and sneak a direction at the same time.
- Circle 70: slip items from the ground directly into personal possession.

### Thief Bonus Notes
- The page emphasizes that thief bonuses strongly affect disarming, lockpicking, lockpick carving, stealing, hiding, and backstabbing.
- Urban bonus is described as being tied to town / justice-linked areas.
- The page explicitly calls out exceptions where in-town areas may still not behave as urban thief bonus zones, including Undershard, Crossing Tunnels, and in-town Ranger guilds.
- `SMIRK <your name>` is described as the way to inspect current confidence and urban bonus state.
- Urban bonus states are described as active urban, neutral, and wilderness, with wilderness potentially being treated as hostile territory for thief comfort.

### Confidence Notes
- The page reinforces that successful risky thief actions such as hiding around creatures, backstabbing creatures, and successful shop theft raise confidence.
- Negative confidence is described as reducing base ranks by `5%` and potentially negating urban bonus.
- Positive confidence stacks with urban bonus.
- The page states that only stealth, backstab, and thievery currently modify confidence.
- The page states that starting khri also checks confidence and that low confidence can prevent some khri from being used.

### Reputation Notes
- Reputation is described as province-specific and not shared globally.
- Reputation drops when the thief is caught breaking the law or stacks charges too quickly in a province.
- Reputation is described as being improved primarily by binning stolen goods in the guild donation bin.
- The page also claims reputation improves from successful creature backstabs that teach and from thiefly tasks for guild-associated NPCs.
- Practical recovery advice from the page: surrender, go to jail, clear fines, stop being wanted, lay low in that province for several real-life days, and bin stolen items when possible.
- Severe reputation penalties described here include being mugged when entering guild areas or passages, severe limb bleeders, and at the worst level, instant death on guild or passage entry.
- Reputation check notes from the page include NPC-specific inquiry routes such as `ASK BEGGAR ABOUT REP` in Crossing and similar sailor / guildleader checks in other provinces.

### Khri Notes
- The page states thieves get their first khri at 1st circle, then one every 5 circles after that.
- Khri are grouped into three trees here: Potency, Finesse, and Subtlety.
- The page names the tree teachers as Kalag in Crossing for Potency, Crow in Riverhaven for Subtlety, and Ivitha in Ain Ghazal for Finesse.
- The page claims all khri can be stacked together with no slot-style stacking cap beyond concentration limits.
- The page notes that starting multiple khri at once has a skill check.
- The page states khri startup difficulty is affected by urban status and confidence.
- The page gives practical posture thresholds for starting khri while standing: roughly tier 1 at 50 magic ranks, tier 2 at 100, tier 3 at 150, tier 4 at 250.
- The page claims slot progression reaches full khri slot coverage by 110th circle.
- The page also describes khri combos as either combo-name driven or producible by activating the constituent khri directly.

### Storage Recommendations Triggered By This Page
- `guild_join_flows` should capture province-specific join routes and gating verbs such as beggar water turn-ins, password sourcing, and escort-based access.
- `guild_access_points` would be useful for passworded or hidden guild entrances by province and city.
- `slip_progression` should normalize the circle-based Slip unlock ladder and its prerequisite teaching model.
- `thief_bonus_states` should normalize Urban Bonus and Confidence states, inspection verbs, and exact gameplay effects.
- `reputation_penalty_states` should capture province reputation bands, entry punishments, and recovery guidance.
- `khri_tree_teachers` should normalize tree-to-teacher mapping and city training locations.
