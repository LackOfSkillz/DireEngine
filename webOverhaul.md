WEB OVERHAUL - MICROTASKS 001-025 (STRICT)
PHASE GOAL

At the end of this set:

OK default Evennia landing page is gone
OK Dragons Ire branded landing page is live
OK hero image is integrated
OK navigation and primary CTA paths work
OK race carousel scaffold is ready for content expansion

CORE PAGE REPLACEMENT (MANDATORY FIRST)
WEB-001 - Replace Website Index Template (LOCKED)

File:

web/templates/website/index.html

Replace contents entirely.

Remove all legacy landing content, including:

Welcome to Evennia
framework copy
developer-facing messaging
Powered by Evennia footer language

No legacy partial includes may remain unless they are still used by the new landing page.

WEB-002 - Create Root Base Template (LOCKED)

File:

web/templates/base.html

Create a new root base template.

Must include:

{% load static %}
complete <head>
font loading for heading and body families
CSS includes for site styling
site header
{% block content %}{% endblock %}
site footer
optional JS block before </body>

Do not inherit from website/base.html.

WEB-003 - Wire Index to New Base Template

File:

web/templates/website/index.html

Index must begin with:

{% extends "base.html" %}

The landing page body must live inside:

{% block content %}
...
{% endblock %}

No other template inheritance path is allowed for this page.

NAVIGATION SYSTEM
WEB-004 - Build Header Navigation and Placeholder Pages

Files:

web/templates/base.html
web/website/urls.py
web/templates/website/world.html
web/templates/website/guilds.html

Add header navigation links:

Home
Play Now
World
Guilds
Lore
Account

Required destinations:

Home -> /
Play Now -> /webclient
World -> /world
Guilds -> /guilds

If /world or /guilds do not already exist, create placeholder routes and minimal branded placeholder templates so these links do not 404.

WEB-005 - Add Account State Logic

File:

web/templates/base.html

Implement Django auth-aware account rendering.

If authenticated:

Welcome, <name>

If anonymous:

Login
Register

Use Django URL tags for auth links rather than hardcoded strings when possible:

{% url 'login' %}
{% url 'register' %}

HERO SYSTEM (CORE FEATURE)
WEB-006 - Add Hero Section Markup

File:

web/templates/website/index.html

Insert hero markup as the first major section inside the content block:

<section class="hero">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <h1>Dragons Ire</h1>
    <p>A living world shaped by skill, risk, and consequence.</p>
    <a href="/webclient" class="btn-primary">Play Now</a>
    <a href="{% url 'register' %}" class="btn-secondary">Create Character</a>
  </div>
</section>

Hero markup must remain minimal and content-first.

WEB-007 - Add Hero Image Assets

Files:

web/static/images/hero/landing_hero_main.jpg
web/static/images/hero/landing_hero_main.webp

Store final hero art in both formats.

The .webp version is the preferred production asset.
The .jpg version is the fallback.

WEB-008 - Apply Hero Background Styling

Files:

web/static/website/css/custom.css
web/templates/base.html

Add hero styling in site CSS.

Minimum requirement:

.hero {
  min-height: 90vh;
  background: url('/static/images/hero/landing_hero_main.jpg') center/cover no-repeat;
}

Preferred production version:

use image-set or equivalent so .webp is served first with .jpg fallback.

WEB-009 - Add Hero Overlay Gradient

File:

web/static/website/css/custom.css

Implement:

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(0,0,0,0.2), rgba(0,0,0,0.75));
}

Overlay must improve text readability without flattening the image.

WEB-010 - Position Hero Text

File:

web/static/website/css/custom.css

Hero text must be:

centered horizontally
slightly above vertical center
layered above overlay
readable on desktop and mobile

WEB-011 - Adjust Hero Focal Point

File:

web/static/website/css/custom.css

If hero subjects are obscured, set:

background-position: center 30%;

This task is complete only when the focal subject remains visible across desktop and mobile breakpoints.

VISUAL IDENTITY
WEB-012 - Apply Locked Color Palette

File:

web/static/website/css/custom.css

Define CSS variables and use them consistently:

background: #0f0f0f
accent: #c89b3c
text: #f5e6c8

No white page backgrounds are allowed.

WEB-013 - Apply Typography System

Files:

web/templates/base.html
web/static/website/css/custom.css

Headers must use a serif display face such as Cinzel.
Body text must use a clean readable sans-serif.

Typography requirements:

load fonts in <head>
assign heading family to h1-h4 and nav accents
assign body family to paragraphs, links, buttons, and meta text

WEB-014 - Style Primary and Secondary Buttons

File:

web/static/website/css/custom.css

Primary button:

gold background
dark text

Secondary button:

transparent background
gold border
gold text

Both buttons must have hover, focus, and keyboard-visible states.

CONTENT SECTIONS
WEB-015 - Add "What Makes This World Different" Section

File:

web/templates/website/index.html

Add a section directly below the hero.

Include 4 feature blocks:

Learn-by-doing progression
Skill-based combat
Living world simulation
Player-driven economy

Each block must contain:

short heading
one-sentence explanation

WEB-016 - Add "Choose Your Path" Section

File:

web/templates/website/index.html

Add a professions section.

Required entries:

Ranger
Warrior
Thief
Mage

Each entry must include:

icon or image slot
profession name
single identity line

Mage remains future-ready but should still render as a valid card.

WEB-017 - Add "The World" Lore Section

File:

web/templates/website/index.html

Add one grounded lore block.

Requirements:

short copy only
grounded tone
no exposition dump
must sound like the game world, not framework marketing

RACE CAROUSEL (CRITICAL FEATURE)
WEB-018 - Add Race Carousel Section Shell

File:

web/templates/website/index.html

Add a section below the content sections:

<section class="race-carousel"></section>

Inside it, create:

section heading
slide viewport container
slide track container
left and right controls

WEB-019 - Create Race Data Source

File:

web/static/website/js/landing.js

Create the JS file if it does not exist.

Define initial data structure:

const races = [
  { name: "Human", role: "Ranger", img: "human.webp" },
  { name: "Elf", role: "Moon Mage", img: "elf.webp" },
  { name: "Dwarf", role: "Warrior", img: "dwarf.webp" }
];

Use 4-6 starter entries.

Image filenames must resolve from a dedicated race asset folder under static.

WEB-020 - Build Carousel Slides

Files:

web/static/website/js/landing.js
web/static/website/css/custom.css

Each slide must render:

media image
dark overlay
name text
role text

Text position:

bottom-left

Important:

use a real <img> element inside each slide, not CSS-only background images, so below-fold race media can be lazy-loaded.

WEB-021 - Add Carousel Navigation Controls

Files:

web/templates/website/index.html
web/static/website/js/landing.js

Add:

left arrow
right arrow
click handlers
keyboard support for previous and next

Controls must work without page reload.

WEB-022 - Add Optional Auto-Rotation

File:

web/static/website/js/landing.js

Implement slow auto-scroll.

Rules:

interval must be between 5000ms and 8000ms
pause on hover
pause on focus inside carousel
easy to disable with a single constant

WEB-023 - Add Mobile Carousel Support

Files:

web/static/website/js/landing.js
web/static/website/css/custom.css

Must support:

swipe gestures
readable text on narrow screens
stacked or simplified layout where needed
touch-safe control sizing

PERFORMANCE AND POLISH
WEB-024 - Optimize Landing and Race Images

Files:

web/static/images/hero/landing_hero_main.webp
web/static/images/hero/landing_hero_main.jpg
web/static/images/races/*

Convert hero and race assets to production-safe sizes.

Rules:

prefer .webp
keep each production asset under 500kb where practical
do not ship oversized source art into static

WEB-025 - Add Native Lazy Loading for Below-Fold Media

Files:

web/static/website/js/landing.js
web/templates/website/index.html

All below-fold race media must use:

loading="lazy"

Do not claim this task complete by applying lazy loading to CSS backgrounds.
If an image must lazy-load, it must be rendered as an image element.

FINAL DESIGN RULES (DO NOT BREAK)

No white backgrounds.
No framework language anywhere.
No demo feel.
No Powered by Evennia footer text.
Everything must match Dragons Ire tone.

IMPLEMENTATION NOTES

Use {% url 'webclient:index' %} for the main play CTA where possible.
Use {% url 'login' %} and {% url 'register' %} for auth links where possible.
Keep all landing-specific CSS in web/static/website/css/custom.css unless a new dedicated file is intentionally created and linked from base.html.
If web/static/website/js/landing.js is created, include it from web/templates/base.html or from a page-level script block.