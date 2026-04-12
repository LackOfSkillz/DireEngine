STATUS UPDATE - March 30, 2026

Implementation status: ECON-021 through ECON-100 are complete in the current codebase.

Validated live behavior now includes strict gem generation and appraisal text, gem pouch auto-storage, search-gated corpse loot, one-time coin/gem/box extraction, corpse and box value caps, specialized vendor rules including pawn handling and `sell all`, banked coins and vault storage, unified carried-weight calculation with coin weight, weighted container capacity, overload pickup/movement rules, and Landing-compatible bank/vault room classification from generated POI data.

Bottom line: DragonRealms does not have one economy. It has several overlapping economies that feed each other:

a coin economy for everyday transactions,
a loot economy from hunting, boxes, skins, gems, and treasure maps,
a service economy driven by profession interdependence,
a player-market economy through trader/player-owned shops and market plazas, and
a crafting/value economy where player-made goods often compete with or exceed baseline shop goods.

For DireMud, the key lesson is that DR’s economy works because combat, survival, support professions, storage, and trade all convert into money through different channels. It is not “kill mob, get gold” in the simple MMO sense.

1) Currency structure

DragonRealms uses three regional currencies: Kronars, Lirums, and Dokoras, with the older Dira treated as obsolete. Each province uses one currency for official and shop transactions, and banks can exchange currencies for a fee. Kronars are also singled out as accepted at vaults regardless of location. Coins further break into denominations like copper, bronze, silver, gold, and platinum, with each denomination worth 10 of the previous one.

That means DR’s money model is doing three things at once:

giving the world regional flavor,
creating light transactional friction,
and still allowing practical conversion through banks.

Design takeaway for you: use a single internal base-unit ledger, but present regional coinage cosmetically or with light conversion friction. DR proves you can have flavorful currencies without making commerce impossible.

2) Banking, storage, and wealth handling

DR’s economy is stabilized by institutional storage:

vaults for item storage,
bank/exchange handling for currencies,
and shop-related bank balances for player-owned shops. Vaults are available in major cities and have meaningful capacity limits; player-owned shops also maintain their own bank accounts and can even hit overflow protections.

This matters because DR does not assume players carry all wealth and goods on their person. That strongly affects:

death risk,
travel logistics,
merchant behavior,
and hoarding control.

Design takeaway: your death system will feel better once coins/items can live in banks, vaults, shops, and graves rather than only “inventory vs lost.” DR’s economy is partly strong because wealth has places to live.

3) Baseline NPC commerce

DR has a large network of ordinary shops, with thousands of cataloged shop items on Elanthipedia. Pawn shops buy a range of items with restrictions, and specialized buyers such as gem buyers and fur traders convert specific loot classes into coin. Donation racks also function as a kind of low-end circulation/recycling mechanism.

That means DR’s NPC economy is specialized, not generic:

gems go to gem buyers,
skins/furs go to fur traders,
broad miscellaneous goods can go to pawn channels,
player shops handle rarer and more differentiated goods.

Design takeaway: do not make one universal “sell all” merchant your main loop. DR’s specialized sinks are part of why loot classes feel distinct.

4) Appraisal as an economic skill

DR’s Appraisal skill is economically important because it lets players estimate value, weight, item qualities, weapon/armor stats, mana capacity, and more. In other words, valuation is partially skill-mediated rather than perfectly transparent.

This is a big design lesson: DR gives players uncertainty, then lets skill reduce that uncertainty. Economic knowledge is not fully free.

Design takeaway: a value/reveal system can make loot feel more physical and more tradable. You do not need total opacity, but partial appraisal improves immersion and creates expertise.

5) The loot economy is multi-channel, not single-channel

In DR, hunting can produce several different reward streams:

coins, gems, and treasure items through loot/search,
boxes through box-dropping creatures,
equipment from creatures,
skins and body parts through skinning,
and special treasure via treasure maps.

The LOOT command itself explicitly separates these categories:

TREASURE for coins, gems, and items like runestones/scrolls,
BOXES for box-only attempts,
EQUIPMENT for creature equipment,
GOODS for treasure + boxes,
ALL for the combined result.

That is a major structural clue. DR treats loot as typed outputs, not one undifferentiated drop table.

Design takeaway: for DireMud, split loot into channels:

cash-equivalent,
container/lock content,
harvestables,
gear,
rare/special objects.

That will make professions and post-combat actions matter.

6) Gems are a major cash-equivalent loot class

Gems are important enough in DR that there are dedicated gem pouches and gem buyers, and treasure map rewards also include gems. The new player guide also frames coin and exchange systems in a way that assumes regular interaction with convertible wealth.

Gems matter because they are:

compact,
valuable,
portable,
and easy to convert into coin.

That makes them an elegant intermediate loot currency.

Design takeaway: gems or compact valuables are excellent for your system because they create meaningful treasure without forcing raw coin inflation in every kill.

7) Boxes are one of DR’s signature loot loops

Boxes are a full subsystem. The Locksmithing skill is largely centered on opening containers dropped by slain creatures, commonly called boxes. There are also hunting ladders specifically cataloging creatures that drop boxes, and combined ladders for creatures that are both skinnable and box-dropping.

This is huge design-wise. DR is saying:

killing a creature is not the end of the reward loop,
post-kill extraction is a skill game,
and not all profitable hunting is equally accessible to every build.

Boxes also create:

trap/pick danger,
profession value for thieves/locksmiths,
social exchange,
and a secondary market in locked goods and box-opening services.

Design takeaway: if you want DR feel, box loot cannot be just “a chest that opens itself.” It should be a secondary resolution layer.

8) Skinning turns kills into a second monetization path

DR’s Skinning skill harvests pieces from slain creatures, and those results can be sold to fur traders or used in creation systems. That means a creature’s economic value is partly determined by what can be extracted from the corpse, not only what it dropped immediately.

This is a different loop from boxes:

boxes reward technical access,
skins reward harvesting skill,
treasure/gems reward search/loot access.

Those layers make one creature produce multiple economic opportunities.

Design takeaway: your loot system should support “corpse processing” as a distinct phase. You already care about death and body-state systems, so this will fit naturally later.

9) Treasure items include utility/magic items, not just vendor trash

The LOOT TREASURE category explicitly mentions items like runestones and scrolls, not just coins and gems. Runestones themselves are economically relevant because they are usable magical devices. Treasure maps can also lead to boxes containing coins, gems, and other prizes, including special item pools.

That means DR treasure mixes:

liquid cash,
utility consumables,
collectible/rare outputs,
and sometimes marketable magic items.

Design takeaway: do not make all non-gear treasure vendor trash. Some of it should be directly useful, tradable, or build-enabling.

10) Hunting ladders matter economically, not just for combat progression

Elanthipedia maintains hunting ladders, plus specific ladders for:

box-dropping creatures,
skinnable creatures,
and overlaps between the two.

That implies a real player behavior pattern: players choose hunts not only by safety or skill training, but by economic profile. Some creatures are attractive because they drop boxes, some because they skin well, some because they do both.

Design takeaway: your future creature design should probably include economic tags like:

skinnable,
box-dropper,
gear-dropper,
gem-rich,
nuisance/low-value,
support-safe.

That will matter more than simple “level.”

11) Player-owned shops are a major endgame/serious-market channel

DR’s Market Plaza houses player-owned shops carrying player-crafted, festival, quest, rare, and unique items. The player-owned shop system includes rent, eviction, local provincial currency, and dedicated shop bank accounts. Market plazas exist in multiple cities, and even market tables provide lighter-weight selling venues.

This matters because DR’s real economy is not only NPC sinks. It also has:

persistent player retail,
geographic markets,
rent pressure,
and professional merchant behavior.

Design takeaway: when you eventually build player commerce, do not treat it as an auction house clone. DR’s shop model is more physical and local, which fits your game much better.

12) Crafting is economically important because player-made goods can outperform shop goods

The forging guide explicitly notes that player-made versions of many tools can be found in plaza shops and are of higher quality than stock society tools. The broader crafting page frames crafting as a large, specialized system with multiple lore skills and disciplines.

This is a crucial economic principle: NPC shops set the baseline, while player production can move into superior-value territory. That creates a healthy relationship between:

starter NPC supply,
advanced crafted demand,
market specialization,
and profession prestige.

Design takeaway: your economy should eventually make merchant stock “good enough to begin” and crafted stock “better enough to matter.”

13) DR’s service economy is real, even if it is not always on a price tag

Because loot extraction and survival depend on specialized skills, DR naturally creates service markets around:

lock opening,
appraisal expertise,
support professions,
and trade channels. The data we looked at does not assign official price schedules for these services, but the structure strongly supports player-to-player monetization.

This is exactly why your completed death/empath/cleric loop will matter economically: once money matters, recovery and support stop being abstract utility and become paid services.

14) DR’s economy has multiple item sinks and friction points

The system avoids being a pure inflation fountain because it has many sinks and friction layers:

bank exchange fees,
shop rent/eviction pressure,
vault constraints,
item specialization by vendor type,
death-related coin/item risk,
and the need to buy tools/materials for crafting.

This is important. DR does not balance its economy only by lowering drop rates. It also uses movement, storage, conversion, upkeep, and specialization friction.

Design takeaway: you do not need punishing taxes everywhere, but you do need sinks beyond repair bills.

What I think DR is really teaching you

The strongest principles worth carrying forward are these:

1. Separate loot classes

DR clearly distinguishes between treasure, boxes, equipment, skins, maps, and special items. That keeps hunting economically varied.

2. Make post-kill extraction matter

Skinning and locksmithing mean profit is not automatic. That is one of the most DR things in the whole model.

3. Use specialized buyers and sinks

Gem buyers, fur traders, pawn channels, market plazas, and vaults create differentiated economic paths.

4. Let player skill reduce uncertainty

Appraisal is not fluff; it makes value legible.

5. Let crafted/player-retail goods surpass baseline NPC goods

That is how the economy graduates from “NPC shop game” to “real player market.”

My recommendation for DireMud architecture

After clerics, I would model your economy/loot system in this order:

Phase A: core coin/value loop

regional or cosmetic currencies backed by one internal base unit
bank deposit/withdraw/exchange
basic shop buy/sell
item value field
coin loss/retention integrated with death

Phase B: typed loot

coins
gems/compact valuables
gear
harvestables
locked containers
rare utility drops

Phase C: extraction loops

search/loot
skinning/harvesting
lockpicking/disarm/open
appraisal/value reveal

Phase D: player market

rentable shops or stalls
local currency handling
persistent listings
lightweight rent/upkeep sink

That sequence matches DR’s structural logic better than jumping straight to crafting or auction-house style trade.

What I would not copy 1:1

I would not copy:

full regional currency complexity at launch,
massive shop sprawl,
or every vendor subtype immediately.

Those work in DR because of long accretion. For your game, the important part is the economic architecture, not cloning every storefront.

multi-channel loot → specialized conversion → banked wealth → risk-integrated economy

These first 20 tasks will establish:

real currency structure
coins on NPCs
typed loot foundation
basic shop conversion
death integration

No fluff. No shortcuts.

🟨 ECONOMY SYSTEM — MICROTASKS 001–020 (DR-CORE FOUNDATION)
🎯 PHASE GOAL

At the end of this set:

👉 NPCs drop coins
👉 Players carry real money
👉 Death risks money
👉 Shops convert goods into coin
👉 Loot system supports multiple categories (foundation)

🪙 CURRENCY SYSTEM (DR-STYLE BASE)
ECON-001 — Define Base Currency Unit

Internally store all money as:

db.coins = int  # base unit (copper equivalent)

All conversions derive from this.

ECON-002 — Define Coin Denominations

Create constants:

COPPER = 1
SILVER = 10
GOLD = 100
PLATINUM = 1000

(1:10 scaling like DR)

ECON-003 — Create Currency Formatter

Function:

format_coins(amount)

Output example:

3 gold, 4 silver, 2 copper
ECON-004 — Add Coin Display to Inventory

Command:

inventory

Shows:

Coins: 2 gold, 3 silver
ECON-005 — Add Add/Remove Coin Helpers
add_coins(amount)
remove_coins(amount)
has_coins(amount)

Must:

prevent negative values
return success/failure
💀 NPC LOOT — COIN DROPS
ECON-006 — Add Coin Field to NPCs

On NPC:

db.coin_min
db.coin_max
ECON-007 — Generate Coins on NPC Death

On death:

coins = random between min/max

Attach to corpse:

corpse.db.stored_coins += coins
ECON-008 — Add Coins to Loot Command

When player loots corpse:

transfer coins → player

Message:

You collect 2 silver and 5 copper.
ECON-009 — Prevent Double Looting

Once coins taken:

corpse.db.coins_looted = True
🪦 DEATH SYSTEM INTEGRATION
ECON-010 — Move Player Coins to Corpse on Death

On player death:

corpse.db.stored_coins = player.db.coins
player.db.coins = 0
ECON-011 — Integrate Depart Coin Logic

Tie into your existing depart modes:

grave → coins stay in grave
items → coins stay
full → coins returned
ECON-012 — Add Coin Recovery from Grave

Extend recover:

restore coins to player
ECON-013 — Add Coin Loss Messaging

On death:

You feel your wealth slip from your grasp as you fall.
💰 ITEM VALUE SYSTEM
ECON-014 — Add Value Attribute to Items

On all items:

db.value = int  # in base coin units
ECON-015 — Add Weight Attribute (Future Hook)
db.weight = float

(Not used yet—but DR relies on it later)

ECON-016 — Add Basic Appraise Command (Stub)

Command:

appraise <item>

Returns:

You estimate this item is worth about X coins.

(No skill system yet—just placeholder)

🏪 SHOP SYSTEM (BASIC DR-LIKE SINK)
ECON-017 — Create Shop NPC Type

File:

typeclasses/npcs/shopkeeper.py
ECON-018 — Add Sell Command

Command:

sell <item>

Behavior:

remove item
give player coins = item value * modifier

Modifier example:

0.5  # 50% value (DR-style loss)
ECON-019 — Add Buy Command (Static Inventory)

Shop has:

db.stock = [items]

Command:

buy <item>
remove coins
give item
ECON-020 — Add Transaction Messaging

Sell:

The shopkeeper hands you 2 silver.

Buy:

You purchase a leather cap for 1 gold.
✅ END STATE AFTER ECON-020

You now have:

✔ Real currency system (denominations + formatting)
✔ NPC coin drops
✔ Loot command integration
✔ Death → coin loss → recovery loop
✔ Item value system
✔ Basic appraisal
✔ Functional shop system (buy/sell)

🧠 WHAT YOU JUST BUILT (IMPORTANT)

You now have the first complete economic loop:

Hunt → Loot coins/items → Sell → Gain wealth → Risk on death → Recover

That is the minimum viable DragonRealms economy core

⚠️ WHAT IS INTENTIONALLY NOT BUILT YET

We are holding back:

gems (major DR system)
boxes / lockpicking
skinning / harvesting
specialized buyers (fur, gem, etc.)
banks / vaults
regional currencies
player shops

Those come next—and they matter a lot.

ECONOMY SYSTEM — MICROTASKS 021–040 (TIGHTENED / LOCKED SPEC)
🎯 DESIGN LOCKS (READ FIRST — NON-NEGOTIABLE)
No procedural “creative” generation beyond defined tables
All gem types, values, and modifiers are explicitly defined below
All randomness must be bounded and deterministic from tables
No new item types beyond those listed
No deviation from value formulas
💎 GEM SYSTEM (FULLY SPECIFIED)
ECON-021 — Create Gem Item Type (STRICT SCHEMA)

File:

typeclasses/items/gem.py

Attributes (ALL REQUIRED):

db.gem_type        # string (from allowed list only)
db.base_value      # int (from table)
db.quality_tier    # int (1–4)
db.size_tier       # int (1–3)
db.final_value     # int (computed, not stored manually)

No additional fields allowed.

ECON-022 — Define Allowed Gem Types (LOCKED TABLE)

Create constant table:

GEM_TYPES = {
    "quartz": 50,
    "amethyst": 100,
    "garnet": 150,
    "opal": 200,
    "topaz": 300,
    "sapphire": 500,
    "emerald": 700,
    "ruby": 900,
    "diamond": 1200
}
Key = gem_type
Value = base_value (in copper units)

No substitutions. No additions.

ECON-023 — Define Quality Tiers (LOCKED)
QUALITY_MODIFIERS = {
    1: 0.8,   # flawed
    2: 1.0,   # average
    3: 1.2,   # fine
    4: 1.5    # exceptional
}
ECON-024 — Define Size Tiers (LOCKED)
SIZE_MODIFIERS = {
    1: 0.8,   # small
    2: 1.0,   # medium
    3: 1.3    # large
}
ECON-025 — Implement generate_gem() (FULLY DEFINED)

Function must:

Select gem_type using weighted distribution:
GEM_WEIGHTS = {
    "quartz": 20,
    "amethyst": 18,
    "garnet": 16,
    "opal": 14,
    "topaz": 10,
    "sapphire": 8,
    "emerald": 6,
    "ruby": 5,
    "diamond": 3
}
Select:
quality_tier = random int (1–4)
size_tier = random int (1–3)
Compute value:
final_value = int(
    base_value *
    QUALITY_MODIFIERS[quality_tier] *
    SIZE_MODIFIERS[size_tier]
)
Return fully constructed gem object.

No deviation allowed.

ECON-026 — Standardize Gem Naming Format

Name must follow:

<size> <quality> <gem_type>

Mapping:

SIZE_NAMES = {
    1: "small",
    2: "medium",
    3: "large"
}

QUALITY_NAMES = {
    1: "flawed",
    2: "average",
    3: "fine",
    4: "exceptional"
}

Example:

large fine ruby
ECON-027 — Add Gems to NPC Loot (EXPLICIT RULE)

On NPC death:

30% chance to generate exactly 1 gem
5% chance to generate 2 gems
Otherwise: no gems

No scaling yet. No variation.

ECON-028 — Add Gem Pouch (STRICT BEHAVIOR)

Item: gem pouch

Rules:

unlimited capacity (for now)
ONLY accepts items of type gem
auto-stores on loot (see next task)
ECON-029 — Auto-Store Gems in Pouch (NO GUESSWORK)

On loot:

IF player has gem pouch:

move gem → pouch

ELSE:

move gem → inventory

No player prompt.

ECON-030 — Gem Appraisal Output (LOCKED TEXT TIERS)

Appraise must output EXACTLY:

Low precision (default):
This appears to be a <size> <gem_type> of <quality> make.
High precision (future hook only, NOT implemented yet):
This is a <size> <quality> <gem_type> worth approximately X coins.

Do NOT implement precision scaling yet.

📦 BOX SYSTEM (STRICT FOUNDATION)
ECON-031 — Create Box Item Type (STRICT SCHEMA)

Attributes:

db.lock_difficulty   # int (1–100)
db.is_locked         # bool (default True)
db.contents          # list (pre-generated)
db.is_open           # bool

No trap system yet. Do not add trap fields.

ECON-032 — Box Drop Rules (LOCKED)

NPC must have:

db.drops_box = True/False

If True:

25% chance to drop exactly 1 box
ECON-033 — Populate Box Contents (STRICT TABLE)

Each box contains:

coins: random 50–200 copper
1 gem (using generate_gem)
20% chance for a second gem

NO items yet. NO randomness beyond this.

ECON-034 — Unlock Command (STRICT SUCCESS MODEL)

Command:

unlock <box>

Behavior:

70% success rate
30% failure → no penalty (for now)

No scaling. No tools yet.

ECON-035 — Open Command (STRICT RULE)

Command:

open <box>

IF locked:

The box is locked.

IF unlocked:

transfer contents to player
mark box empty
ECON-036 — Prevent Double Opening

After open:

db.is_open = True

Further attempts:

The box is empty.
ECON-037 — Box Weight (LOCKED VALUE)

All boxes:

db.weight = 5.0

No variation yet.

ECON-038 — Box Appraisal Output
This appears to be a locked container of moderate weight.

No value reveal.

🏪 SPECIALIZED BUYERS (STRICT RULES)
ECON-039 — Vendor Type Definitions (LOCKED)

Define:

VENDOR_TYPES = ["general", "gem_buyer"]
ECON-040 — Vendor Behavior Rules (NO DEVIATION)
General Shop:
accepts: all items EXCEPT gems
payout: 50% of item value
Gem Buyer:
accepts: ONLY gems
payout: 90% of gem value
✅ RESULT

Now Aedan has:

✔ Exact gem list
✔ Exact value formulas
✔ Exact drop rates
✔ Exact box contents
✔ Exact vendor rules
✔ Zero ambiguity

🧠 WHY THIS MATTERS

You just prevented:

content drift
inconsistent economies
hidden inflation bugs
“creative interpretation” errors

This is how DR stays stable over decades.

ECONOMY SYSTEM — MICROTASKS 041–060 (STRICT / DR EXPANSION)
🎯 PHASE GOAL

At the end of this set:

👉 Loot becomes multi-step (DR-style)
👉 Corpses support separate extraction phases
👉 Loot is not automatically revealed
👉 Vendors behave more like DR (structured acceptance)
👉 Economy begins enforcing friction + control

🔍 SEARCH VS LOOT SYSTEM (DR CORE BEHAVIOR)
ECON-041 — Add Corpse Search State

On corpse:

db.searched = False

Default: False

ECON-042 — Modify Loot Command Behavior

Command:

loot <corpse>

IF:

corpse.db.searched == False

THEN:

You need to search the corpse first.

No fallback. Hard block.

ECON-043 — Create Search Command (STRICT)

Command:

search <corpse>

On success:

sets:
corpse.db.searched = True

Message:

You search the corpse carefully.
ECON-044 — Search Reveal Output (LOCKED)

After search, output EXACTLY:

coins (if present)
gems (count only, not details)
box (if present)

Example:

You find:
- some coins
- a gemstone
- a small box

Do NOT reveal gem type or value.

ECON-045 — Prevent Repeated Search Spam

If already searched:

You have already searched this.
💰 LOOT EXTRACTION RULES (STRICT)
ECON-046 — Split Loot Into Categories

On corpse:

db.has_coins = True/False
db.has_gems = True/False
db.has_box = True/False

These are set during NPC death.

ECON-047 — Loot Coins Only Once

On loot <corpse>:

IF coins exist AND not looted:

transfer coins
set:
db.coins_looted = True
ECON-048 — Loot Gems Only Once

On loot:

transfer ALL gems at once
set:
db.gems_looted = True
ECON-049 — Loot Box Only Once

On loot:

transfer box
set:
db.box_looted = True
ECON-050 — Corpse Empty Detection

If ALL:

coins_looted == True
gems_looted == True
box_looted == True

Then:

There is nothing else of value here.
⚖️ LOOT BALANCE CONTROL (ANTI-INFLATION)
ECON-051 — Enforce Coin Drop Cap

NPC coin generation:

coins = min(random(min,max), 200)

Hard cap: 200 copper per NPC

ECON-052 — Enforce Gem Value Cap Per Corpse

Max total gem value per corpse:

max_gem_value = 1500

If exceeded:

downgrade highest value gem until within cap
ECON-053 — Limit Box Spawn Value

Box total contents must not exceed:

max_box_value = 2000

Apply same downgrade logic as gems.

ECON-054 — Prevent Multi-Box Drops

NPC can drop:

max_boxes = 1

No exceptions.

🏪 VENDOR SYSTEM EXPANSION (STRICT)
ECON-055 — Add Pawn Shop Vendor Type

Update:

VENDOR_TYPES = ["general", "gem_buyer", "pawn"]
ECON-056 — Pawn Shop Rules (LOCKED)

Pawn shop:

accepts: ALL items (including gems)
payout:
gems: 70%
items: 60%
ECON-057 — Enforce Vendor Rejection Order

When selling:

Check vendor type
Check accepted_item_types
If not accepted → reject

NO fallback logic.

ECON-058 — Add “sell all” Command (STRICT)

Command:

sell all

Behavior:

sells ONLY items accepted by vendor
skips invalid items silently
ECON-059 — Add Sell Summary Output

After bulk sell:

You sell several items for a total of X coins.

Must show total only (no per-item spam).

ECON-060 — Add Vendor Inventory Sink (ANTI-EXPLOIT)

After buying item:

item is NOT resold by vendor
item is destroyed (removed from game)

This prevents:

buy/sell loops
value duplication exploits
✅ END STATE AFTER ECON-060

You now have:

✔ Search → Loot separation (true DR behavior)
✔ Multi-phase corpse interaction
✔ Hidden loot until discovered
✔ Strict extraction rules
✔ Inflation caps
✔ Vendor specialization (expanded)
✔ Bulk selling
✔ Exploit prevention

🧠 WHAT JUST CHANGED (IMPORTANT)

You moved from:

Kill → instantly get everything

to:

Kill →
  Search →
    Discover →
      Extract →
        Convert →
          Profit

That is core DragonRealms identity.

⚠️ NEXT CRITICAL SYSTEM

You now have:

boxes
unlocking stub
vendor economy
typed loot

👉 But boxes are still shallow.

We are going to implement:

bank accounts (coin storage)
vaults (item storage)
strict access + location rules
transaction friction (light, DR-accurate)
no ambiguity
🟨 ECONOMY SYSTEM — MICROTASKS 061–080 (BANK + VAULT — STRICT)
🎯 PHASE GOAL

At the end of this set:

👉 Players can deposit/withdraw coins
👉 Players can store items safely
👉 Death risk is reduced through banking
👉 Wealth becomes distributed, not carried
👉 Location matters

🏦 BANK ACCOUNT SYSTEM (COINS)
ECON-061 — Add Bank Balance Attribute (STRICT)

On character:

db.bank_coins = 0  # stored in base unit (copper)

No other currency fields allowed.

ECON-062 — Create Bank Location Tag

Rooms that support banking must have:

room.db.is_bank = True

All bank commands MUST check this.

ECON-063 — Create Deposit Command

Command:

deposit <amount>
deposit all

Rules:

only works in is_bank rooms
amount must be ≤ player coins
moves coins → bank_coins
ECON-064 — Deposit Validation (STRICT)

Reject if:

not in bank:
You must be at a bank to do that.
invalid amount:
You do not have that much.
ECON-065 — Deposit Execution
player.db.coins -= amount
player.db.bank_coins += amount

No rounding. No fees yet.

ECON-066 — Deposit Messaging (LOCKED)
You deposit X coins into your account.
ECON-067 — Create Withdraw Command

Command:

withdraw <amount>
withdraw all
ECON-068 — Withdraw Validation

Reject if:

not in bank
amount > bank_coins

Message:

You do not have that much in your account.
ECON-069 — Withdraw Execution
player.db.bank_coins -= amount
player.db.coins += amount
ECON-070 — Withdraw Messaging
You withdraw X coins from your account.
🧾 ACCOUNT VISIBILITY
ECON-071 — Create Balance Command

Command:

balance

Output:

On hand: X coins
In bank: Y coins

Use formatted currency output.

ECON-072 — Prevent Bank Use While Dead

If player is DEAD:

You cannot access your account in this state.
🧱 VAULT SYSTEM (ITEM STORAGE)
ECON-073 — Add Vault Storage Attribute

On character:

db.vault_items = []

This stores item references or IDs (implementation-dependent but consistent).

ECON-074 — Create Vault Location Tag

Rooms that support vaults:

room.db.is_vault = True

Bank and vault may coexist, but must be checked separately.

ECON-075 — Create Store Command

Command:

store <item>

Rules:

must be in vault room
item must be in inventory
item must NOT be:
worn
equipped
ECON-076 — Store Execution
remove item from player
append to:
player.db.vault_items
ECON-077 — Store Messaging
You place <item> into storage.
ECON-078 — Create Retrieve Command

Command:

retrieve <item>

Rules:

must be in vault
item must exist in vault_items
ECON-079 — Retrieve Execution
remove item from vault_items
add to player inventory
ECON-080 — Retrieve Messaging
You retrieve <item> from storage.
⚠️ HARD RULES (NO DEVIATION)
Vault is infinite capacity for now (do NOT add limits yet)
Vault is 100% safe from death loss
Banked coins are 100% safe from death loss
No fees yet (we add later)
No shared accounts
No remote access
No partial failure states
✅ END STATE AFTER ECON-080

You now have:

✔ Banked currency (safe from death)
✔ Withdraw/deposit loop
✔ Vault item storage
✔ Physical location requirement
✔ Separation of:

carried wealth (risk)
stored wealth (safe)
🧠 WHAT JUST CHANGED (CRITICAL)

Before:

All wealth = always at risk

Now:

Wealth is a decision:
  Carry → risk
  Store → safe

👉 This is one of the most important DR behaviors

⚠️ WHAT’S NEXT (IMPORTANT)

Now that banking exists, you unlock:

1. Coin weight (now meaningful)
2. Travel risk decisions
3. Economic hoarding behavior
4. Real death tension
🔜 NEXT BLOCK (RECOMMENDED)

Now we should tighten the system further:

👉 BANK EXPANSION (STRICT)
coin weight system
deposit/withdraw limits
transaction fees
regional banks (optional later)



ECONOMY SYSTEM — MICROTASKS 081–100
WEIGHT + ENCUMBRANCE SYSTEM (STRICT / UNIFIED)
🎯 DESIGN LOCKS (NON-NEGOTIABLE)
ALL weight is calculated in a single unit: weight units (float)
ALL objects that can be carried MUST have weight
Coins have weight
Containers have:
base weight
contents weight
No “weightless” exceptions
Encumbrance affects gameplay (movement/combat hooks later)
⚖️ CORE WEIGHT SYSTEM
ECON-081 — Add Weight Attribute to ALL Objects

Every item must have:

db.weight = float

Defaults:

if not set → reject object creation (no fallback allowed)
ECON-082 — Define Weight Unit Standard (LOCKED)

Define:

WEIGHT_UNIT = 1.0

Reference:

dagger ≈ 1.0
sword ≈ 3.0
armor piece ≈ 5–15

(No scaling logic yet—just standardization)

ECON-083 — Add Coin Weight Constant (LOCKED)

Define:

COIN_WEIGHT = 0.002

Meaning:

500 coins = 1.0 weight

No deviation.

ECON-084 — Add get_coin_weight()
def get_coin_weight(coins):
    return coins * COIN_WEIGHT
ECON-085 — Add Character Total Weight Calculation

Create:

def get_total_weight(self):

Must include:

inventory items
worn items
coins
ECON-086 — Add Container Weight Inclusion

If item is container:

total_weight = base_weight + sum(contents_weight)

Must recurse fully (nested containers supported)

ECON-087 — Prevent Infinite Recursion

Add safety:

max container depth = 5

If exceeded:

stop calculation
log error
🎒 INVENTORY + CARRY SYSTEM
ECON-088 — Add Max Carry Weight Attribute

On character:

db.max_carry_weight = 100.0

No scaling yet.

ECON-089 — Add Encumbrance Ratio Calculation
encumbrance = total_weight / max_carry_weight

Store:

db.encumbrance_ratio
ECON-090 — Define Encumbrance Thresholds (LOCKED)
Ratio	State
<0.5	Light
<0.8	Moderate
<1.0	Heavy
≥1.0	Overloaded
ECON-091 — Add Encumbrance State Getter
def get_encumbrance_state():

Returns string from table above.

🚫 CARRY RESTRICTIONS
ECON-092 — Block Item Pickup When Overloaded

If:

total_weight >= max_carry_weight

Block:

You are carrying too much to pick that up.
ECON-093 — Allow Temporary Overload Edge (STRICT)

Allow:

pickup that causes overload

BUT:

block further pickup

(This matches DR feel—brief overburden allowed)

ECON-094 — Block Movement When Heavily Overloaded

If:

encumbrance >= 1.2

Block movement:

You are too encumbered to move.
🪙 COIN INTEGRATION
ECON-095 — Integrate Coin Weight into Total Weight

In get_total_weight():

total += get_coin_weight(self.db.coins)
ECON-096 — Update Inventory Display with Weight

Add:

Weight: X / Y
Encumbrance: Moderate
ECON-097 — Add Coin Weight Messaging

If coins exceed threshold:

The weight of your coins is becoming noticeable.

Trigger at:

10% carry capacity from coins

🎒 CONTAINER SYSTEM (STRICT)
ECON-098 — Define Container Capacity

Containers must have:

db.max_capacity_weight
ECON-099 — Block Overfilling Containers

If:

contents_weight > max_capacity_weight

Block:

There is no room for that.
ECON-100 — Add Container Weight Display

When examining container:

Weight: X (contents: Y)
Capacity: Y / Z
✅ END STATE AFTER ECON-100

You now have:

✔ Unified weight system
✔ Coins have real physical impact
✔ Containers behave realistically
✔ Carry limits enforced
✔ Encumbrance states defined
✔ Movement restrictions (basic)

🧠 WHAT JUST CHANGED (CRITICAL)

Before:

Carry everything → no consequence

Now:

Carry choices matter:
  Coins vs items
  Boxes vs mobility
  Loot vs survival

👉 This is a core DragonRealms pressure system

⚠️ WHAT’S STILL MISSING (NEXT LAYER)

Now that weight exists, DR behavior expects:
