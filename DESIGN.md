---
name: Phish Blue Team Console
description: A bright, evidence-forward security console where the grey ramp builds every surface and only a verdict may be saturated.
colors:
  plane: "#f4f5f7"
  card: "#ffffff"
  sunken: "#eef0f4"
  line: "#dfe3e9"
  line-strong: "#cbd2dc"
  ink: "#101a2e"
  ink-2: "#4a5a72"
  ink-3: "#5c6b82"
  brand: "#e05c33"
  brand-hover: "#c9471f"
  brand-ink: "#b03d18"
  brand-tint: "#fdeee8"
  brand-edge: "#f4d2c4"
  good-fill: "#e7f4ec"
  good-ink: "#0f7a34"
  good-mark: "#0ca30c"
  good-edge: "#bfe3cd"
  warn-fill: "#fdf1d6"
  warn-ink: "#8a5a06"
  warn-mark: "#fab219"
  warn-edge: "#eed9a6"
  bad-fill: "#fdeaea"
  bad-ink: "#b3261e"
  bad-mark: "#d03b3b"
  bad-edge: "#f2c4c1"
typography:
  display:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "25px"
    fontWeight: 800
    lineHeight: 1.12
    letterSpacing: "-0.025em"
  hero-figure:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "52px"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.03em"
  figure:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "30px"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "20px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "normal"
  title:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  body-small:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "0.07em"
  column-head:
    fontFamily: "Manrope, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.04em"
    fontFeature: "tnum"
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  key: "2px"
  input: "8px"
  surface: "10px"
  pill: "999px"
  circle: "50%"
spacing:
  xs: "6px"
  sm: "10px"
  md: "14px"
  lg: "18px"
  xl: "24px"
  xxl: "30px"
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
    typography: "{typography.body-small}"
  button-primary-hover:
    backgroundColor: "{colors.brand-hover}"
    textColor: "{colors.card}"
  button-primary-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.ink-3}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  button-secondary:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  button-secondary-hover:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.ink}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.brand-ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  panel:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "18px"
  tile:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "14px 16px"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.input}"
    padding: "9px 12px"
  nav-item-active:
    backgroundColor: "{colors.brand-tint}"
    textColor: "{colors.brand-ink}"
    rounded: "{rounded.input}"
    padding: "9px 12px"
  input-text:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.input}"
    padding: "12px"
    typography: "{typography.mono}"
  badge-phishing:
    backgroundColor: "{colors.bad-fill}"
    textColor: "{colors.bad-ink}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  badge-suspicious:
    backgroundColor: "{colors.warn-fill}"
    textColor: "{colors.warn-ink}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  badge-legitimate:
    backgroundColor: "{colors.good-fill}"
    textColor: "{colors.good-ink}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  verdict-banner-phishing:
    backgroundColor: "{colors.bad-fill}"
    textColor: "{colors.bad-ink}"
    rounded: "{rounded.surface}"
    padding: "20px 22px"
---

# Design System: Phish Blue Team Console

## Overview

**Creative North Star: "The Lit Evidence Room"**

This is a security console built for a bright room and a projector, not a darkened SOC. It refuses the category default — neon-on-black tiles, glow, sparklines — because that look asks to be trusted rather than earning it. Instead a cool-neutral grey ramp does all the structural work, ink is navy-black rather than pure black, and saturated colour is rationed so hard that its appearance is information. Every number on screen can be traced back to the header or the sentence that produced it, and the type ramp exists to make that chain readable: one loud figure, one label, then quiet supporting text at 12–13px.

Density is high but never crowded. Cards are white islands on a grey plane, separated by a single hairline and a ground shift rather than by shadow; the whole app ships zero `box-shadow` declarations. Buttons are fully-rounded pills, headings are heavy (800) and tightly tracked, and the one accent hue — a warm orange — is confined to chrome that could never be mistaken for a verdict. The world is materially flat and typographically confident.

Two things in this build diverge from the direction contract that preceded it, and **the shipped CSS is the truth**: the contract specified a navy `#1b3a63` primary action with "no brand accent hue at all" and "system sans throughout", while the build ships a two-step orange brand ramp (`#e05c33` fill, `#b03d18` text) and Manrope loaded from Google Fonts at 400–800. The contract's reasoning against a *green* brand still holds and is honoured: the accent is orange precisely because it cannot be confused with any verdict band.

**Key Characteristics:**
- Light, cool-neutral grey ramp carrying every surface and border; no dark mode.
- Zero shadows; depth is ground shift plus one hairline.
- Saturated colour reserved for the verdict triad plus one orange accent for chrome.
- Manrope at 800 for figures and headings; everything supporting at 12–13px.
- Fully-rounded pill buttons and 10px surface cards.
- One orchestrated entrance animation, then stillness.
- Every text colour measures at or above 4.5:1 against its own ground.

## Colors

A cool grey ramp with one warm orange accent and a three-band status triad; nothing else on screen is allowed to be saturated.

### Primary
- **Signal Orange** (`#e05c33`): the accent fill. It appears on the primary action pill, on contribution bars in the "Why this score" table, and as the caret colour in text fields. Chrome only.
- **Burnt Orange Ink** (`#b03d18`): the text-safe step of the same hue. Every orange *word* uses this, not the fill: links, ghost buttons, the active nav label. It is also the `:focus-visible` ring colour on every control. 5.95:1 on white, 5.46:1 on the plane.
- **Deep Ember** (`#c9471f`): hover only. The primary pill darkens to this on hover, which is the point at which its label can flip to white (4.77:1); on the resting fill, white measures 3.65:1 and fails.
- **Orange Wash** (`#fdeee8`) with edge **Orange Hairline** (`#f4d2c4`): the tinted pill behind the active nav item — enough to locate yourself in the rail without flooding it.

### Secondary
The verdict triad. Each band is a two-step ramp — a pale tint fill plus a much darker ink — so it reads on both the white card and the grey plane, plus one saturated mark used only as a chart fill or key.

- **Clear Green** (fill `#e7f4ec`, ink `#0f7a34`, mark `#0ca30c`, edge `#bfe3cd`): legitimate. Ink measures 4.81:1 on its own fill.
- **Caution Amber** (fill `#fdf1d6`, ink `#8a5a06`, mark `#fab219`, edge `#eed9a6`): suspicious. Ink measures 5.28:1 on its own fill.
- **Alarm Red** (fill `#fdeaea`, ink `#b3261e`, mark `#d03b3b`, edge `#f2c4c1`): phishing. Ink measures 5.64:1 on its own fill; it is also the error-state colour for `role="alert"` panels and inline field errors, and the underline under a highlighted risky phrase.

### Neutral
- **Console Plane** (`#f4f5f7`): the page ground. Everything raised sits on it.
- **Card White** (`#ffffff`): raised surfaces — panels, tiles, the topbar, text fields, secondary buttons.
- **Sunken Grey** (`#eef0f4`): recessed wells — the raw message `<pre>`, hovered table rows, hovered nav items, the pie's empty track, the unknown badge.
- **Hairline** (`#dfe3e9`): the default 1px border on every surface and every table rule.
- **Hairline Strong** (`#cbd2dc`): the heavier 1px border that marks an *interactive* edge — inputs, secondary buttons, the disabled primary's dashed outline, scrollbar thumbs.
- **Navy Ink** (`#101a2e`): all primary text and every figure. 15.92:1 on the plane.
- **Slate Ink** (`#4a5a72`): secondary text — subtitles, notes, evidence cells, legend labels. 6.42:1 on the plane.
- **Muted Ink** (`#5c6b82`): tertiary text — micro-labels, placeholders, column heads, tile shares. 4.96:1 on the plane, 4.74:1 on sunken grey; this is the floor of the ramp and nothing paler may carry text.

### Named Rules

**The Verdict Monopoly Rule.** Green, amber and red belong to the verdict triad and to nothing else. A chart, a tag, a chrome state or an illustration may not borrow a band colour for a meaning other than legitimate / suspicious / phishing. The accent is orange specifically so that no piece of chrome can be read as a verdict.

**The Two-Step Ramp Rule.** Every coloured family ships a fill step and a darker ink step, and text always takes the ink step. Orange fill `#e05c33` carries dark navy ink (4.75:1), never white. Amber `#fab219` measures 1.68:1 on the plane and green mark `#0ca30c` measures 3.08:1 — both are fill-and-mark only, never text, never a border carrying meaning alone.

**The Never-Colour-Alone Rule.** The triad is the classic deuteranopia pair, so a band never travels as colour by itself: it always ships colour plus its written label plus its square key mark. Pie slices carry `<title>` tooltips and a directly-labelled legend with counts and percentages; the bar chart column carries a screen-reader header and per-bar `aria-label`.

## Typography

**Display Font:** Manrope (fallback `system-ui`, `-apple-system`, "Segoe UI", Roboto, sans-serif), loaded from Google Fonts at weights 400, 500, 600, 700, 800.
**Body Font:** Manrope — the same family does everything.
**Label/Mono Font:** the platform mono stack (`ui-monospace`, SFMono-Regular, Menlo, Consolas) for machine text only.

**Character:** Manrope is a geometric sans with generous counters and a nearly-circular 'o', which keeps a dense 12.5px table legible while still looking modern at 52px. The system uses only its extremes — 800 for anything that is a number or a heading, 400 for prose — so hierarchy comes from weight jumps and tight negative tracking rather than from many sizes.

### Hierarchy
- **Hero Figure** (800, 52px, 1.0 leading, -0.03em): the verdict score in the banner, coloured in its band's ink. The single loudest element in the product; one per screen at most.
- **Figure** (800, 30px, 1.05, -0.02em): stat tile counts, and the pie's centre total at 26px. Band-coloured in the three verdict tiles, navy in the neutral "Scanned" tile.
- **Display** (800, 25px, 1.12, -0.025em): the page `h1` — "Analyze", "History".
- **Headline** (650, 20px, 1.2, capitalized): the verdict word beside the hero figure.
- **Title** (700, 16px): panel `h2` headings, and the wordmark at 800/-0.02em. A title may carry a trailing 12.5px muted note on the same baseline row ("contributions add up to 87").
- **Body** (400, 15px, 1.5): the document default.
- **Body Small** (400, 12.5–13px): subtitles, notes, table cells, legends, button labels. This is where most of the app's words actually live.
- **Label** (700, 11px, 0.07em, uppercase): stat tile labels and the wordmark's "blue team" descriptor.
- **Column Head** (600, 11px, 0.04em, uppercase, muted ink): real `<th scope="col">` text in every table.
- **Mono** (400, 12–12.5px): raw headers, field values, the pasted message body, quoted phrase codes. Machine text, never UI chrome.

### Named Rules

**The Tabular-Where-It-Aligns Rule.** `font-variant-numeric: tabular-nums` is applied only to digits that stack in a vertical column — numeric table cells, weight columns, badge scores, legend ranges, pie legend values, the domain-age input. Hero and tile figures use Manrope's proportional figures, because a single large number reads better kerned than gridded.

**The Micro-Label Ceiling Rule.** Uppercase wide-tracked 11px labels sit above a *number* or beside the wordmark, and nowhere else. They must never be used as a kicker or eyebrow over a heading, and 10px is the absolute floor of the type ramp — reached only once, by the wordmark's descriptor.

**The One Family Rule.** There is no display face, no serif, no second sans. Anything that wants to feel different gets a weight change or the mono stack, not a new family.

## Layout

A sticky full-bleed topbar over a centred single column. The topbar (`#ffffff`, 10px × 24px padding, bottom hairline, `z-index: 10`) holds the wordmark, a vertical hairline divider, the two nav pills, a flex spacer, then the live API/DB status chip on the right. The content column is `max-width: 1160px`, centred, padded 26px / 30px / 48px.

Inside the column, everything is a stack of full-width panels separated by 14px. The KPI row is a 4-column equal grid with 12px gutters; the composition pie sits in a flex row with a 28px gap between the 160px donut and its direct-labelled legend, wrapping when narrow. Detail views use a two-column `104px 1fr` label/value grid with hairlines between rows.

The spacing rhythm is small and even-numbered: 6 / 10 / 14 / 18 / 24 / 30, with 2px used only for micro-offsets and for the surface gaps between pie segments. Panel padding is 18px; tile padding is 14px × 16px.

Two breakpoints, both narrowing rather than restructuring: at **1000px** the KPI grid drops to 2 columns; at **720px** the topbar wraps and tightens to 14px side padding, the content column drops to 16px side padding, the verdict banner's right-hand block and the legend left-align instead of right-aligning, truncated table cells shrink from 320px to 180px max, and the label/value grid collapses to a single column. There is no mobile drawer or hamburger — the nav is two pills and simply wraps.

## Elevation & Depth

**No shadows.** The build contains zero `box-shadow` and zero `text-shadow` declarations, and that is a deliberate invariant, not an omission. Depth is carried by exactly two devices: a **ground shift** (white card or sunken grey well against the grey plane) and a **single 1px hairline**. Raised means whiter than its ground; recessed means greyer than its ground; interactive means the hairline steps up from `#dfe3e9` to `#cbd2dc`.

The one gradient in the stylesheet is not decoration: the highlighted-phrase `<mark>` paints its tint as a two-stop `linear-gradient` of the same colour purely so `background-size` can be animated from 0 to 100% for the sweep-in.

### Named Rules

**The Hairline-Not-Shadow Rule.** Separation is a border and a ground change. Never add a `box-shadow` to lift a card, a dropdown, a modal or a hover state — raise the surface colour or step the border up to `#cbd2dc` instead.

**The Still-After-Entrance Rule.** Motion is one orchestrated entrance and then stillness. Contribution bars draw left-to-right in descending order of contribution (520ms, `cubic-bezier(0.16, 1, 0.3, 1)`, staggered 70ms per row), and after them the flagged phrases sweep their highlight in (420ms, same curve, starting at 560ms, staggered 90ms per span) — score, then factors, then the exact words. Nothing else animates except 120ms colour/background transitions on nav items and pie segments. All of it is disabled under `prefers-reduced-motion: reduce`.

## Shapes

Two corner families, used for opposite purposes. **Surfaces are gently rounded rectangles at 10px** (panels, tiles, the verdict banner). **Controls that are text-on-a-shape are fully-rounded pills at 999px** — every button, every badge, the contribution bars, the scrollbar thumb. Inputs and nav items sit between them at 8px, soft enough to belong to the surface family while reading as typeable. Small squares are 2px (the 9px verdict key marks); state dots and the API status dot are true circles.

Borders are always exactly 1px and always a ramp grey; nothing carries a 2px border except the underline beneath a highlighted risky phrase (2px, band mark colour) and the `:focus-visible` ring (2px solid `#b03d18`, 1px offset). The disabled primary button is the one dashed edge in the system: rather than dimming to 50% opacity — which read as broken rather than waiting — it goes transparent with a dashed strong-hairline border and muted ink, and states what it is waiting for.

Icons are authored inline SVG on a 24-viewBox, 17px rendered, `fill: none`, `stroke: currentColor`, `stroke-width: 1.7` (2 when the nav item is active), round caps and joins, 0.85 opacity at rest and 1 when active.

## Components

### Buttons
- **Shape:** fully-rounded pill (999px), 9px × 18px padding, 13px label.
- **Primary:** Signal Orange fill (`#e05c33`) with **navy ink** (`#101a2e`) at weight 700 — 4.75:1. White on this fill measures 3.65:1 and is forbidden.
- **Hover / Focus:** the fill darkens to Deep Ember (`#c9471f`) and only then does the label flip to white (4.77:1). Focus shows a 2px `#b03d18` ring at 1px offset, never a shadow.
- **Disabled:** transparent with a dashed `#cbd2dc` border and muted ink at full opacity; the label states what it is waiting for rather than dimming.
- **Secondary:** white fill, strong hairline border, navy ink at 600; on hover the fill goes to sunken grey and the border to muted ink.
- **Ghost:** transparent, borderless, Burnt Orange Ink label with a 3px-offset underline — for low-stakes affordances like "load sample".

### Chips
- **Style:** the verdict badge is a pill (999px, 3px × 10px, 12px/700, capitalized, `white-space: nowrap`) carrying its band's tint fill, band ink, and band edge border. Its trailing score is bold and tabular.
- **State:** an unscored item takes the `unknown` variant — sunken grey fill, slate ink, default hairline. Badges are read-only status, not filters.

### Cards / Containers
- **Corner Style:** 10px.
- **Background:** Card White on the Console Plane.
- **Shadow Strategy:** none; see Elevation & Depth.
- **Border:** 1px Hairline. When a panel is also a drop target, dragging swaps the border to Signal Orange.
- **Internal Padding:** 18px (tiles 14px × 16px, verdict banner 20px × 22px).

### Inputs / Fields
- **Style:** Card White fill, 1px strong-hairline border, 8px radius. The main paste field is mono 12.5px with 12px padding and vertical-only resize; selects and small number inputs are 7px radius with 6px × 8px padding. Caret colour is Signal Orange.
- **Focus:** 2px `#b03d18` `:focus-visible` ring at 1px offset, applied uniformly to textareas, buttons, selects, inputs and links.
- **Error:** the field or panel takes Alarm Red's fill, edge and ink, and the container carries `role="alert"`.

### Navigation
- **Style:** two horizontal pills in the sticky topbar, each a drawn 17px SVG icon plus a 500-weight label at 8px radius, slate ink on transparent.
- **Hover:** sunken grey fill, ink darkens to navy; 120ms transition.
- **Active:** Orange Wash fill, Orange Hairline border, Burnt Orange Ink label at 700, icon at full opacity and 2px stroke.
- **Mobile:** no drawer. The topbar wraps and tightens its padding; the pills stay visible.

### Verdict Banner (signature)
The verdict takes over the KPI row's position as a band-flooded panel: the band's tint fill, the band's edge as its border, the score at 52px/800 in the band's ink, the capitalized band word beside it, and under that the coverage line ("out of 100 · 78% of signals measured"). The right side carries the full three-band legend with key marks and score ranges — the active band bolded to navy — plus the deterministic-only score for comparison. The band never appears without its word and its key.

### Contribution Bars (signature)
Inside the "Why this score" table, each factor's share is a 7px fully-rounded Signal Orange bar in a 30%-wide column, width set as a percentage of the score, drawn in on entrance in descending order of contribution. The bar column's header is screen-reader-only and each bar carries `role="img"` with an `aria-label` stating its points, because the bar is a second encoding of the adjacent numeric cell, never the only one.

### Highlighted Phrase (signature)
A risky phrase quoted from the analysed message renders as a `<mark>` inside the sunken mono body well: Alarm Red ink, Alarm Red tint background, a 2px `#d03b3b` bottom rule, 2px corners. Its tint sweeps in left-to-right after the bars finish. Message bodies are always rendered as text in a `<pre>`, never as HTML.

## Do's and Don'ts

### Do:
- **Do** build every surface from the grey ramp: Card White raised, Sunken Grey recessed, Console Plane as the ground, one 1px hairline between them.
- **Do** put dark navy ink on the orange fill and reserve white for the darker hover step (`#c9471f`, 4.77:1).
- **Do** use `#b03d18` for any orange that is a word, a link, or a focus ring, and `#e05c33` only for fills.
- **Do** ship every verdict as colour plus its written label plus its square key mark.
- **Do** keep tabular figures to columns that align vertically, and leave hero and tile figures proportional.
- **Do** draw icons as inline SVG at `stroke-width: 1.7` with round caps on a 24 viewBox.
- **Do** keep real `<thead>` / `<th scope="col">` markup, `role="alert"` on errors, `aria-live` on async states, and a `:focus-visible` ring on every control.
- **Do** hold the type floor at 11px for labels, 12px for mono, 12.5px for prose.
- **Do** honour `prefers-reduced-motion: reduce` by removing the entrance animation entirely.

### Don't:
- **Don't** add a `box-shadow` or `text-shadow` anywhere. Raise the surface or step the border to `#cbd2dc` instead.
- **Don't** let green, amber or red mean anything other than legitimate, suspicious or phishing.
- **Don't** set `#fab219` or `#0ca30c` as text or as a meaning-bearing border — they measure 1.68:1 and 3.08:1 on the plane and are fill/mark only.
- **Don't** put white type on `#e05c33`.
- **Don't** introduce a second type family, a serif, or a display face; weight and the mono stack carry the contrast.
- **Don't** use a unicode character as an icon — arrows, checks, bullets and dots are all authored SVG or CSS shapes.
- **Don't** place an uppercase wide-tracked micro-label above a heading as a kicker or eyebrow; it belongs above a number.
- **Don't** express a discrete verdict as a continuous green-to-red gradient track — a three-hue continuous ramp is the rainbow scale, and the bands are states, not a magnitude.
- **Don't** dim a disabled control to low opacity; give it a dashed edge and a label that says what it is waiting for.
- **Don't** render an attacker-supplied message body as HTML; it goes into the mono `<pre>` as text.

---

**Verification note.** No browser-based screenshot round was possible in this session — no browser automation was available. This system was verified by computing contrast ratios directly from the shipped token values, by the bundled detector, by typecheck, and against the user's own screenshots. It has not been confirmed by an automated visual pass, so measurements here are exact while composition claims rest on the source and those screenshots.
