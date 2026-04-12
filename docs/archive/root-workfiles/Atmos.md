# Moon Mage Ambient Messaging - DireLore Compilation

> Primary source: live DireLore PostgreSQL data queried on 2026-04-07.
> Primary tables used: `sections`, `raw_pages`, and `page_metadata`.
> Scope: Moon Mage ambient dialogue, introductory speech, guildleader flavor lines, sect representative speech, and closely related guildhall atmosphere pulled from the DireLore DB.
> Deduplication note: DireLore currently contains duplicate title variants for some quest pages, especially `100th_Circle_Moon_Mage_quest` and `100th_Circle_Moon_Mage_Quest`. Duplicate text has been collapsed here.

---

## 1. What This File Includes

This file is organized by the NPC or speaker who delivers the message.

It includes:

- preserved introductory and onboarding speech
- ambient guildleader banter and personality lines
- peer-commentary lines where one Moon Mage talks about another
- Circle 100 quest speech preserved in the DB
- sect-representative speech where the database preserves actual wording
- a short final section for speakerless guildhall atmosphere that helps frame the NPC messaging

It does **not** invent missing dialogue. When the database only preserves a route or an `ASK` prompt but no actual speech, that is noted directly.

---

## 2. Guildleaders

### Kssarh T'Kinnirii

#### Core personality and presentation

DireLore preserves Kssarh as the harsh, abrasive, black-humored Crossing trainer.

Key descriptive beats:

- constant frown
- paces in barely controlled anger
- enjoys intimidation as pedagogy
- treats novices as burdens who must prove they are worth his time
- expresses genuine joy for Moon Mage craft under the hostility

#### Guild pitch / join atmosphere

> Kssarh mumbles to himself as he glares at you in obvious annoyance. He looks none too happy at your presence in his office, and paces about in barely-controlled anger.

> Kssarh's constant frown softens a bit, and he almost seems to smile as he says "Ah, yes, our guild... The finest in all the lands!" He lets out a gleeful cackle and then regains his composure once again.

> "Well, Moon Mage," he continues, "Suffice to say that we Moon Mages are without a doubt the most important people who walk the lands today! It is we who may read the stars and planets above, who may feel the magical caress of the moonlight as it streams upon our upturned faces, and who may hear in the whispering of the winds the changes in the weather to come."

> Kssarh glowers at you. "Well?" he asks. "If you think you want to become a Moon Mage, then JOIN. If you do not, then get out of my blasted observatory!"

> Kssarh chortles with glee! "Now you belong to me!"

> Kssarh yanks you by your ear over to a large stack of tomes and shoves you down into a chair. "Now listen up!"

#### Training and philosophy lines

> "Now pay attention, young man, because if you miss anything it's the Barbarian Guild for you!"

> "Well, Master Moon Mage, if you're wondering who's in charge around here, it's me. So when you want something, such as spells or training in the ways of the guild, just drag your sorry carcass in here, and if you're lucky we may actually help you -- but don't count on it!"

> "You'll probably fail, like most of the spineless beggars who wander through this place, but if it does come to be that you have a bit of potential... we'll teach you a bit about the mysteries of the heavens above."

> "We shall teach you a bit of magic -- spells and words of wondrous power." He extends one cupped hand toward you, and for a moment you see it filled with a pool of blackness. Within the pool, you see the dancing vision of a starry, cloudless sky. Kssarh then snaps his fingers, and the vision vanishes.

> "Now listen here, Moon Mage. You will learn two things: The rudiments of magic, and the ways of observing the heavens to make those prognostications for which we Moon Mages are so famous."

> "To predict the future, young Moon Mage, you must first OBSERVE the various heavenly bodies. Since you are but an initiate of the guild at this time, it would be best that you restrict your observations to the moons and the sun. Then, once you have observed their aspects sufficiently, all you must do is listen to your inner voice and PREDICT the future!"

> "A word of warning to you, Moon Mage. Use your powers as you will, but bring shame upon this guild by acting foolishly, and you will find me quite the harsh taskmaster! Remember that you represent ALL Moon Mages when you speak your words of prophecy!"

> "Being that you haven't given me a reason to throw you in the sewers with the death spirits yet today, if you ask me about magic you just MIGHT get to learn a new spell."

#### Short response flavor

Book response:

> Kssarh stares at you as if you were wearing a tunic made of fish heads. "If you don't quit wasting my time, your next lesson will be one in flying. Now, which spellbook did you wish to know about?"

Sect response:

> "Look, runt. With the resolution of the Mirror Wraith Prophecy, all the Moon Mage subguilds have set up shop in various areas around Elanthia. The Celestial Compact is here in this guildhall, but if you can't find the entrance then we don't very well want you as a member. Now get out of my face."

Wrong-spell response:

> "That's not one of our bloody spells! Now cultivate some sense before we send you to the Empath guild in a wooden crate!"

#### Kssarh talking about other people

These are valuable because they show his tone toward peers and institutions.

About Gylwyn:

> "Apparently, a pretty face and a nice smile can get you your own guild, but I'd resign before I let the Council stick me in a tent, and in Riverhaven, no less! A filthy city, that is."

About Lomtaun:

> "He's a good enough mage, I suppose, though anyone who is that happy all the time can't be all right in the head. He must be thrilled to get visitors out there in the middle of nowhere."

About Mortom:

> "Mortom's not too bad. I don't know what he needs all those mirrors for, but if you want some artifact or device looked at, there's none better."

About Tiv:

> "Tiv was my teacher once, and a damn good one, at that, even if he is too quiet."

#### Circle 100 quest messaging

Reminder if asked again:

> Kssarh snorts and glares at you. "You're really pushing your luck, aren't you? You know where to go, but since you're acting like a worthless guttersnipe runt, I'll spell it out for you: T-A-I-S-G-A-T-H. And if you can't figure it out from THAT, you don't deserve to ever get promoted again."

Completion reaction:

> Kssarh's frown curls slowly into a grin as you approach him. "Well now, I've heard you're not so worthless as we were all so sure you were! Tell me what you have learned."

> "You've learned that the stellar bodies form intricate patterns, just like those that drive our spells, our skills, and even our contact with the Probability Plane!"

> "A Moon Mage's power is very deeply linked to everything in the sky. We are Celestial Mages, but it is the four moons which aid us the most... With the understanding you have now, you can latch onto these small fragments rather than die like a worthless guttersnipe on a failed Teleport!"

#### Implementation takeaway

Kssarh messaging should read as:

- hostile but not cruel for cruelty's sake
- proud of the guild to the point of arrogance
- educational through ridicule, pressure, and contempt
- occasionally delighted when a student proves worthy

---

### Cherulisa D'Shari'sendal

#### Core personality and presentation

Cherulisa is preserved as the opposite pole from Kssarh:

- spiritually framed
- solemn and instructive
- steppe- and spirits-oriented
- poetic without losing practical instruction
- calm, severe, and culturally rooted

#### Introductory speech

> "The spire of the Trabe is a symbol of the Moon Mage Guild. We climb as high as we dare to touch the stars. Our enchantments create strange and wondrous things, and our past is filled with grief."

> "We walk under the moons, facing the world with magic and foresight in place of the swords of the Barbarians and the spears of our past. A Moon Mage must journey through the shadows, but always brings with her the light of knowledge into the dark places."

> "If you have come here to learn the art of the shamans of the steppe and the Moon Mage Guild, ask to JOIN the guild so that we may begin your education."

> "The spirits say you have potential, and I agree with them in this, but you must also show conviction."

> "You have come far to train under the shamans of the steppe, and you will not find us lacking. We will begin immediately."

#### Onboarding and Moon Mage identity

> For several weeks you study the lore of the Moon Mage Guild with Cherulisa in her spire and around campfires on the Arid Steppe. You are taught the fundamentals of Lunar magic and your senses seem to grow sharper as you begin to practice divination.

> "Moon Mages find solace beneath the moons and starlight. There are many that say we walk in darkness, that our hearts are cold and our mysteries unnatural. They do not know the truth: a Moon Mage brings light into the darkness, just as the stars pierce the veil of night. Never forget this truth, and never let the light of your knowledge dim."

> Cherulisa walks to a window and pulls its curtain aside, gesturing to the sky as a gust of frigid wind sweeps in. "The spirits speak to all Moon Mages, giving us wisdom beyond our years and beyond now. They speak to us through the moons, the sun, and the multitude of stars above us. You would do well to listen."

> "A faint sense of the spirits is always with you, granting you a clarity of sight and sensation others lack. Yet to gain deeper knowledge, you must observe the movement of the heavens."

> "But there is more to life than the heavens! ... we are the unquestioned masters of Lunar magic. With the aid of the spirits, we teach the bizarre geometry of teleportation spells, the manipulation of light and shadow, clairvoyance and yet stranger magic."

> "Many Moon Mages learn the art of the sigils... Others fancy themselves as masters of the planes, walking down paths that twist in ways you cannot now imagine, to catch a glimpse at the heart of the universe."

#### Steppe / tribe / culture speech

Nomads:

> "The Nomads of the Arid Steppe are one people and one tribe, forged by the peace of Kir Dor'na'torna."

Ways:

> "Dangerous. Even if the Naming Ritual makes it easier to navigate and cross between the planes, terrible and violent things have stalked the conduits since that day."

Bonedancers:

> "Not a tribe, not a people. The Bonedancers are madmen who make a mockery of our culture and the peace of Kir. Stay well away from them if you value your sanity and your life."

Windwalker / geometry heritage:

> "They taught us much about what is now called enlightened geometry and the use of teleportational energy."

#### Cherulisa talking about other Moon Mages

About Gylwyn:

> "Sweet personality, soft mind."

About Kssarh:

> "I will not speak of Kssarh, except to say that he is the perfect man for his job."

About Lomtaun:

> "We do not speak much, but I respect him and his traditions. We both live in lonely spires, though I think I get out more often."

About Mortom:

> "There are easier and less time consuming ways to come back from the dead."

About Tiv:

> "He is called a wise man, he speaks the words of wise men, and performs the action of a wise man. But tell me this: Would a wise man sit in the middle of a volcano?"

#### Circle 100 quest messaging

Reminder if asked again:

> Cherulisa chuckles, points east and says, "You've already been told what you must do. Head to Taisgath and learn. May the spirits guide you."

Promotion gate speech:

> Cherulisa gets a serious look on her face and says, "The spirits have guided you well. No longer a child but becoming a man. Make the long journey to Taisgath, and there you will find the true nature of what it is to be a Moon Mage."

Completion reaction:

> Cherulisa closes her eyes and calmly smiles as you explain what you learned from the artifact on Taisgath.

> "The stellar bodies form intricate patterns, very much like the ones that drive our spells, our skills and our contact with the Plane of Probability. We are bound to the universe, and the universe is bound to us."

> "Teleporting can be fatal if cast without a moonbeam... at least to someone who does not understand the nature of the universe. A true Moon Mage such as yourself can latch onto the small fragments of Grazhir that fell to Elanthia to establish an anchor point in lieu of a moonbeam."

#### Implementation takeaway

Cherulisa messaging should read as:

- grounded in spirits, stars, and memory
- less sarcastic than Kssarh
- still firm and serious
- capable of turning instruction into almost ceremonial wisdom

---

### Lomtaun Nedorath

#### Core personality and presentation

The dedicated NPC page is sparse, but the quest text preserves Lomtaun's tone clearly:

- patient
- fated / prophetic
- calm and paternal
- confident that history is unfolding as expected

#### Descriptive beat

> Guildmaster Lomtaun is a tall slight form behind the lectern... he contemplates the eye of the mosaic whirlpool serenely.

#### Circle 100 gate speech

Initial warning:

> Lomtaun smiles and says, "No more promotions for you, young <Character Name>. Here on the isle of Sky Magic is where Fate has brought you, and now it is time for a greater experience. Ask me again about this experience, and I shall speak on what is required of you."

Completion reaction:

> Lomtaun notices as you approach him, and before you can say a single word, begins to speak. "I foresaw this moment... My predictions were true, as Fate would will, for within your eyes I see that knowledge."

> "Congratulations, for you have learned the connections that form the basis for our magic and our guild. The intricate patterns the stellar bodies form are just like those that drive our spells, our skills, and even our powers of foresight."

> "A Moon Mage's powers are inextricably linked to the four moons... with this understanding... you can now latch onto the small fragments of Grazhir rather than die on a failed Teleport."

#### Implementation takeaway

Lomtaun should sound like:

- someone who already expected the answer
- a teacher of fate rather than a taskmaster
- quietly pleased when prophecy resolves correctly

---

### Gylwyn

#### Core personality and presentation

DireLore preserves little direct standalone speech from Gylwyn, but what does survive is consistent:

- warm
- encouraging
- softer than Kssarh and less mystical than Cherulisa
- proud of the student's progress

#### Presentation beat

> Gylwyn is without a doubt the most beautiful Halfling lady you have ever seen... her gentle presence leaves no doubt in your mind that she is a queen among people wherever she may go.

#### Circle 100 gate speech

Initial push toward Taisgath:

> Gylwyn smiles faintly at you and says, "I am thrilled to see your dedication to our art, but you need to learn something words alone cannot express to progress beyond this point. Go to the island of Taisgath and search for meaning."

Reminder if asked again:

> Gylwyn looks at you with concern. "You've already been told what you must do. The next step in your education lies on Taisgath. I would do you an injustice to let you advance without learning this."

Completion reaction:

> Gylwyn smiles brightly at you. "Congratulations! I knew you could do it! Tell me what you found on Taisgath."

> "Do you understand now why words alone could not encompass this? Just as our art is bound in patterns and systems of order, so are the heavens bound in the same."

> "Though Grazhir fell long ago, something of it remains with us... With your awareness as your aegis, you never need to fear a misplaced moonbeam with Teleport again."

> "Wonderful! Your accomplishments have brought you far."

#### Space-linked atmosphere

The Riverhaven guildhall places her in a fitting setting:

- glass-domed balcony
- driftwood desk
- books and parchments
- open sky access through the spire

That makes her voice feel scholarly and welcoming rather than severe.

---

### Mortom Saist

#### Core personality and presentation

Mortom's preserved text paints him as:

- elegant and vain
- mirror-fixated
- artifact-minded
- intellectually dangerous
- smoother than Kssarh, but stranger than Gylwyn

#### Presentation beat

> Though an elderly Human, Guildleader Mortom Saist looks remarkably good for his age... it is clear that Mortom is aware of his better-than-average appearance, for he occasionally pulls a hand mirror from his crimson robes, or gazes longingly into any of the varied ones that hang nearby.

#### Circle 100 gate speech

Initial push toward Taisgath:

> Mortom gives you a thoughtful look. He smiles, sighs, and then removes his spectacles to give them a good polishing. "I'm pleased with your progress. It's time you traveled to see Lomtaun on Taisgath. There are things you must know before I will discuss promotions again."

Reminder if asked again:

> Mortom says, "Hmm. I do believe you've been told to go to Taisgath. Upon your return I will be more than ecstatic to speak with you."

Completion reaction:

> Mortom gazes into a nearby mirror as you speak to him about what you've learned on Taisgath, almost as if he were not paying attention at all.

> "Excellent. I do mean that. Now you see that the stellar bodies form intricate patterns, very much like the ones that drive our spells, our skills and our contact with the Plane of Probability."

> He holds a mirror up to your face. "Look inside the source of your own power. You have an understanding now. You can latch onto the small fragments of Grazhir that fell to Elanthia to establish an anchor for your magic -- Teleporting without a moonbeam is no longer fatal, but a boon!"

> "Excellent, excellent. No longer an initiate, but a true seeker of knowledge."

#### Implementation takeaway

Mortom should sound like:

- vain but perceptive
- almost distracted until he reveals he was listening closely
- visually obsessed with reflection, mirrors, and self-regard

---

### Tiv Guildermann

#### Core personality and presentation

Tiv survives mostly through descriptive material and quest dialogue, but his voice is strong:

- contemplative
- austere
- perfection-focused
- wise without being sentimental

#### Presentation beat

> Guildmaster Tiv coldly surveys his platform, hovering over the volcano floor far below.

#### Circle 100 gate speech

Initial push toward Taisgath:

> Tiv fails to answer you immediately, taking a long moment to look you over with a calm expression. "My student. Every step we take brings us closer to perfection, a goal some claim is impossible... It is time for you to speak to Lomtaun on Taisgath for what comes next."

Reminder if asked again:

> Tiv smiles. "You have already been told what you must do. Please, do not fight fate. Travel to Taisgath, and speak to Lomtaun."

Completion reaction:

> Tiv steeples his fingers and looks up at your approach. "Is it strange for an old man to recognize knowledge in a young Elothean's face and to feel joy at his part in bringing about that knowledge?"

> "No, perfection is a journey which even after years of study is some distance off."

> "You have gained one more key and taken one more step along the path to enlightenment... Our powers are linked to the four moons inextricably; they are as much a part of us as our arms or our minds."

> "With this comprehension... you can now latch onto the small fragments of Grazhir rather than die on a failed Teleport."

#### Implementation takeaway

Tiv should read as:

- quiet and severe
- philosophical rather than mystical
- committed to self-mastery and perfection

---

## 3. Sect Representatives

### Scarlet-robed mage

This is the only sect representative for whom the current DB snapshot preserves actual speech.

Source: `Category:Progeny_of_Tezirah`, heading `Sect Representative Speech`.

> "The Progeny of Tezirah was originally formed by a magess named Tezirah Eilsina. During the times of the Empire, any slightly questionable act of magic was dubbed as sorcery, and shamefully, Tezirah was accused."

> "Officially, she was executed near the present day city of the Crossing, but many believe she managed to cast one final spell of vengeance on her would-be murderers, escaping into the Plane of Probability."

> "Some distastefully claim that it is Tezirah who attacks Moon Mages as they tap the Plane of Probability via prediction, appearing in the form of a bat-winged skull."

> "Historically, the Crowther family has always represented the Progeny of Tezirah on the Council of Moon Mages... Like many Tezirites, the Crowthers are known for their skill and artistry with shadow magic."

### Other sect representatives with location preserved but no speech block found

The current DireLore snapshot preserves the contact routing for these sect reps, but not standalone ambient speech pages for them:

- stuffy junior officer: Celestial Compact, Crossing guildhall
- colorful gypsy: Fortune's Path, Taisgath
- cheerful representative: Heritage House, Throne City
- hooded monk: Monks of the Crystal Hand, Halls of Ith'Draknari
- ancient shaman: Nomads of the Arid Steppe, Trabe Plateau
- blind prophet: Prophets of G'nar Peth, Kweld Andu tent

For these NPCs, the database currently supports their identities and locations, but not a speech archive comparable to Kssarh, Cherulisa, or the scarlet-robed mage.

---

## 4. Quest-Only Group Dialogue

These lines are not tied to dedicated NPC pages, but they are still preserved speaker-by-speaker and are useful as ambient reference.

### Promotion gate reminder set

- Kssarh: aggressive ridicule and impatience
- Cherulisa: calm redirection with spiritual blessing
- Tiv: patient admonition not to resist fate
- Gylwyn: concern that the student not skip an essential lesson
- Mortom: amused but firm insistence on Taisgath first

### Circle 100 completion set

All guildleaders converge on a few shared Moon Mage truths:

- the stellar bodies form intricate patterns analogous to Moon Mage spells and skills
- Moon Mage power is tied to four moons, not merely the visible three
- Grazhir's fragments become a viable anchor once the initiate truly understands the profession's cosmic structure
- failed Teleport without a visible moon stops being purely fatal after this realization / advancement

The differences are tonal, not doctrinal:

- Lomtaun frames it as fulfilled prophecy
- Kssarh frames it as finally proving you are less worthless than expected
- Cherulisa frames it as spiritual and cosmic truth
- Tiv frames it as another step toward enlightenment
- Gylwyn frames it as joyful understanding
- Mortom frames it as a mirror-held revelation of internal power

---

## 5. Ambient Space Without a Speaker

These are not NPC voice lines, but they strongly support the mood the NPCs should inhabit.

### Riverhaven guildhall / Obsidian Spire

Entrance:

- winding stair into darkness
- cold blue-white tzgaa lights in stair risers
- paintings tucked beneath the steps

Balcony:

- subtly tinted glass dome
- greenery beds receiving rain
- desk covered in books and parchments
- Gylwyn present beside an alabaster scroll

Roof:

- sky visible through cutaways in the shell of the spire
- seating lip, plant channel, telescope
- Grazhir shard `Taniendar`

### Why this matters

The NPC messaging above should be staged in rooms that feel like:

- observatories
- spires and balconies
- books, parchments, and instruments
- sky-facing scholarship
- isolation, height, and dangerous knowledge

---

## 6. Best Reusable Voice Patterns

If you need a fast implementation guide for NPC bark generation or static dialogue trees, the strongest preserved Moon Mage voices are:

### Kssarh pattern

- insult first
- praise only when earned
- guild supremacy as obvious truth
- stars and prophecy discussed like hard craft, not vague wonder

### Cherulisa pattern

- calm, spiritual cadence
- stars and spirits as living instruction
- darkness balanced with knowledge and light
- strong steppe / tribe memory

### Lomtaun pattern

- serenity
- fate already knew you were coming
- lessons framed as the unfolding of an expected pattern

### Gylwyn pattern

- warm praise
- joy in the student's growth
- less severity, more confidence and encouragement

### Mortom pattern

- polished vanity
- mirrors, surfaces, reflection, poise
- unsettling calm before incisive insight

### Tiv pattern

- self-mastery
- perfection as horizon, not destination
- sparse words with deliberate weight

---

## 7. Global DireLore Atmospherics Index

This appendix broadens the file beyond Moon Mage-only material.

The current DireLore snapshot contains at least these distinct atmosphere-adjacent records in the major buckets you asked for:

- `npc`: 111 records
- `items`: 31 records
- `actions`: 18 records
- `combat`: 3 records
- `spell_system`: 12 records
- `room_area`: 5 records

There is also a much larger miscellaneous and system bucket outside those categories, but the lists below cover the direct NPC, combat, item, action, and closely related atmosphere records requested.

### NPC Atmospherics

- Abira | Atmospherics
- Aged Su Helmas expedition archeologist | Flavor Messaging
- Agitated businessman | Atmospheric Messages
- Ahlema | Atmospherics
- Almalne Alolan (housing) | Atmospherics
- Archrost | Summary from the message boards, 18 May 2002
- Auriril | Speech at Guildfest 409
- Bardon | Atmospherics
- Barstook | Atmospherics
- Belirendrick III | Post from DR message boards
- Betina | Atmospherics
- Blorg | Atmospherics
- Bradyn | Atmosphere
- Brokk | Atmospheric Messaging
- Budd | Room Messages
- Calorak | Atmospherics
- Chabalu | Atmospherics
- Cheerful Elven peddler | Atmosphere
- Cherulisa | Introduction Speech
- Chesum | Atmospheric Messaging
- Cleric wrapped tightly in dark robes | Atmosphere
- Concerned arachnologist | Atmospheric Messages
- Crafty Cat | Atmospherics
- Daralaendra | Atmospheric Messaging in Daralaendra's Office
- Disheveled architect | Atmospherics
- Diwitt | Atmospherics
- Dokt | Atmospheric Messaging
- Dokt | Former Atmospheric Messaging
- Dumi | Atmospherics
- Dwarf, A (prediction tools) | Idle Messages
- Eaadrich | Atmospheric Messaging
- Elpalzi fomenter | Speech
- Elpalzi partisan | Speech
- Elven gardener | Atmospherics
- Elven Warden (2) | Atmospherics
- Emberclaw Expedition | Atmospherics
- Eorie | Atmospheric Messaging
- Fade | Speech Responses
- Faysien | Atmospheric Messaging
- Festive Elf | Atmospherics
- Festive tailor | Atmospherics
- Footpad (creature1) | Speech
- Footpad (creature2) | Speech
- Footpad (creature3) | Speech
- Footpad (creature4) | Speech
- Footpad (creature5) | Speech
- Geprofa | Atmospherics
- Gnome workman | Dialogue
- Gudthar | Atmospherics
- Hilda | Atmospherics
- Holy weapon | Introduction Speech
- Hugh | Atmospherics
- Jackwater | Atmospherics
- Jalihh | Atmospherics
- Kalika | Ranger Introduction Speech
- Knobby | Atmospherics
- Kriley | Atmospheric Messages
- Krrikt'k | Atmospherics
- Kssarh | Moon Mage Introduction Speech
- Ladar | Atmospherics
- Lalbot | Atmospheric Messaging
- Les | Circle Message
- Lileyew | Bard Introduction Speech
- Lilidona | Atmospherics
- Macfrae | Bard Introduction Speech
- Master consultant | Atmospheric Messaging
- Masul | Atmospherics
- Nezhiri | Atmosphere
- Rancois | Atmospherics
- Rangu | Atmospherics
- Raven (npc) | Atmospherics
- Revia | Atmospheric Messages
- River Elf, A | Atmospheric Messaging
- Robyn | Dialogue
- Rotting deadwood dryad | Dialogue
- S'Kra Kor shaman (1) | Speech
- S'Kra Kor warrior (1) | Speech
- Sazu | Atmospheric Messaging
- Scruffy-looking priest | Atmospherics
- Selinthesa | Bard Introduction Speech
- Serdal | Atmospherics
- Shisthlin's Works | Atmospherics
- Silvyrfrost | Bard Introduction Speech
- Smavold | Atmospherics
- Spider Cage | Atmospheric Messages
- Su Helmas expedition graveyard explorer | Flavor Messaging
- Su Helmas expedition ziggurat climber | Flavor Messaging
- Tasdrean | Bard Introduction Speech
- Tehya | Atmospherics
- Thalorin | Messaging
- Therengian guide | Atmo Messaging
- Thrumgrin | Atmospherics
- Thug (creature1) | Speech
- Thug (creature2) | Speech
- Thug (creature3) | Speech
- Thug (creature4) | Speech
- Thug (creature5) | Speech
- Tidworth | EZAtmo Items
- Tomas | Atmospherics
- Tuzra | Atmospheric Messaging
- Unspiek | Atmospherics
- Urglub | Atmospherics
- Urivael | Atmospheric Messages
- Ushei | Atmospherics
- Woodhut | Atmospherics
- Wyla | Atmospherics
- Yaziyi | Bard Introduction Speech
- Yolesi | Atmospherics
- Yorgi | Atmospheric Messaging
- Young flowergirl | Atmospherics
- Zezinka | Room Messaging

### Item Atmospherics

- Item:A pale moon coral octopus with riftstone-striped tentacles | Atmo Messaging
- Item:Achaedi crystal | Messages
- Item:Adorable white bunny figure displaying sharp fangs | Messaging
- Item:Agate signet ring with a stylized gladiolus | Possible READ Messages
- Item:Aged jade tailband | Messaging
- Item:Articulated kraken figurine with abyssal black eyes | Siegery Messaging
- Item:Braided armure anklet dangling spherical-shaped vengeance ruby charms | Atmospheric Messaging
- Item:Bright reddish-orange persimmon costume composed of lustrous taffeta | Atmospheric messaging
- Item:Clockwork windsteel ring featuring miniature articulated wings | Atmos
- Item:Dainty spun glitter slippers adorned with star-cut twilight sapphires | Atmospheric messaging
- Item:Dark moonstone that resembles Katamba | Atmos
- Item:Encyclopedic almanac carefully bound with a shadowleaf cover | Messaging
- Item:Everdusk damite starling charm | Atmo Messaging
- Item:Fierce snow hawk charm with piercing geobloom eyes | Atmo Messaging
- Item:Golden eagle feather strung on a heartname leather cord | Atmos
- Item:Grey pygmy owl charm displaying swirling charoite eyes | Atmo Messaging
- Item:Inky black diacan raven charm adorned with agonite-limned feathers | Atmo Messaging
- Item:Miniature Dwarven enforcer figurine wrought from crimson moonsilver | Death Message
- Item:Miniature fortune teller enveloped in layers of garishly bright treasureweave | Messaging
- Item:Miniature shark figurine with a polished steel body | Messaging
- Item:Ornate horned headdress adorned with an abundance of vibrant velvet lilies | Atmospheric messaging
- Item:Piece of foil | Atmo Messages
- Item:Pig | Atmospherics
- Item:Prismatic glass medallion | Atmo
- Item:Rugged morgawr leather almanac with waxed pages | Messaging
- Item:Sleek truegold firebird charm with crimson sapphire-tipped wings | Atmo Messaging
- Item:Snake charm | Atmospheric messaging (slithers around on person)
- Item:Steel-tipped cured leather backsheath tooled with the visage of a roaring lion | Messaging
- Item:Stormfire topaz ring spiral-set in platinum | Atmos
- Item:Tincture jar | Messaging:
- Item:Translucent icicle | Atmo Messaging

### Action, Arrival, and Departure Atmospherics

- Arachnomancy (1) | Advent (Arrival Messages)
- Arachnomancy (1) | Departure (Depart Messages)
- Arachnomancy (2) | Advent (Arrival Messages)
- Arachnomancy (2) | Departure (Depart Messages)
- Bawdy swain | Arrival Messages
- Chaen | Depart Message Options
- Chaen | Using the Depart Message
- Cordulia | Entrance & Exit Messages
- Haros | Entry and Exit Messaging
- Iocanthe | Arrival & Departure Messages
- Katoak | Custom Depart Messages
- Klusarlaik | Depart Messaging
- Koror | Arrival & Departure Messages
- Lawlite | Entrance & Exit Messaging
- SimuCoins | Custom Depart Messaging
- Starlight Sphere | Movement Messages
- Winna | Arrival & Departure Messages
- Ynami | Entry & Exit Messaging

### Combat Atmospherics

- Combat | Combat Messaging
- Holy weapon | Sample Combat Messaging
- Hylomorphic Corruption | Damage messaging

### Spell and System Messaging That Reads Like Atmosphere

- Aegis of Granite (2.0) | Additional Spell Messaging
- Arachnomancy (1) | Incantation (Spell Preparation Messages)
- Arachnomancy (2) | Incantation (Spell Preparation Messages)
- Fire Rain (2.0) | Spell Messaging
- Heal (2.0) | Spell Messaging
- Heal Scars | Spell Messaging
- Heal Scars (2.0) | Spell Messaging
- Heal Wounds | Spell Messaging
- Heal Wounds (2.0) | Spell Messaging
- Osrel Meraud | Power Messaging
- Retreat command | Successful Messaging
- Retreat command | Unsuccessful Messaging

### Room, Area, and Weather Atmospherics

- Harst Haalm | Area Atmospherics
- Ignite | Weather-related atmospherics
- Midhik Haalm | Area Atmospherics
- Tower Base | Area Atmospherics
- Weather | Atmospheric

### Additional Missed Source Pages Worth Tracking

These are not part of the requested NPC, item, action, and combat core, but they are clearly atmosphere-adjacent and easy to miss in a narrower pass:

- Category:Atmospheric items | Pages in category "Atmospheric items"
- Category:Forehead gems | Variations with Atmospherics
- Category:Living spider cloaks | Atmospheric Messaging
- Category:Progeny of Tezirah | Sect Representative Speech
- Arachnomancy (1) | Incantation (Spell Preparation Messages)
- Arachnomancy (2) | Incantation (Spell Preparation Messages)
- Retreat command | Successful Messaging
- Retreat command | Unsuccessful Messaging
- Weather | Atmospheric

### Coverage Note

This appendix is an index of the distinct DireLore pages and headings currently carrying atmosphere-style messaging in the requested buckets.

It is not a full raw-text dump of every message line from every one of those `111 + 31 + 18 + 3 + 12 + 5` records. If you want that next, the logical follow-up is to split the corpus into bucket files such as:

- NPC bark dump
- item atmo dump
- combat and action messaging dump
- room and weather atmo dump