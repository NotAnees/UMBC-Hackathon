---
version: 1
slug: "frontend-src"
primary_target: "frontend/src"
related_targets: []
---

---
version: 1
slug: "frontend-src"
primary_target: "frontend/src"
related_targets: []
---

# Surface brief — blue-team console (`frontend/src`, React on :5173)

Scope: the whole blue-team console — Analyze, History, Verdict detail. Visitor mode: **Operate** (an analyst decides whether a message is an attack, then acts).

Audience: the person triaging a suspicious email — a teammate during the demo, a judge watching it, an analyst in the real scene. Bright room, projector, minutes not hours.

Job: read a verdict, believe it, act. Task frequency: bursts of many messages, then drill-in on one.

Proof available: every score decomposes into weighted factors; the AI pass quotes the exact phrases it objected to; the red team supplies ground truth so catch-rate is real, not claimed.

Constraints: the two static dashboards on :8000/:8001 are test rigs and are no longer a consistency obligation — this surface is the demo. Attacker-controlled email bodies are never rendered as HTML. The AI pass is often unavailable (quota), so partial coverage is a permanent state, not an error.

## Direction contract

**THESIS.** The score shows its work: every number traces to the exact header or sentence that produced it, and partial knowledge is stated rather than hidden. It refuses the category default — the dark SOC wall of neon-on-black tiles, sparklines and glow — because that look asks to be trusted instead of earning it. Calm, light, legible, evidence-forward.

**OWN-WORLD.** Light grey enterprise-security console. A cool-neutral grey ramp does all structural work: page plane `#f4f5f7`, raised cards `#ffffff`, hairline borders `#dfe3e9`, navy ink `#101a2e`, secondary `#4a5a72`, muted `#6b7a92`. No shadows — surfaces separate by ground shift and hairline. **The verdict triad owns every saturated pixel in the product**, each band as a two-step ramp of tint fill plus darker ink so it reads on grey: legitimate `#e7f4ec` / `#0f7a34`, suspicious `#fdf1d6` / `#8a5a06`, phishing `#fdeaea` / `#b3261e` (all 4.8–6.0:1, measured). Chart marks use the validated status steps `#0ca30c` / `#fab219` / `#d03b3b`. Primary action is navy `#1b3a63` — deliberately outside the triad, so no chrome can be mistaken for a verdict. No brand accent hue at all: the greys brand it, status carries meaning. System sans throughout, no display or serif face. Tabular figures only in columns that align vertically; hero and tile numbers take proportional figures.

**STORY.** The visitor sees, within one viewport, how much of their inbox is suspect. They understand this message's verdict and why, believe it because the evidence is quoted from their own email rather than asserted, and act: drill in, mark the verdict wrong, or move on.

**FIRST VIEWPORT.** Slim left rail (Analyze / History). Across the top a KPI row of four stat tiles — Scanned, Phishing, Suspicious, Legitimate — each a hero-scale proportional number over a small label, the three verdict tiles carrying their band key mark. Beneath the row, one horizontal stacked bar showing the inbox as part-to-whole across the three bands, 2px surface gaps between segments, direct labels. Then the Analyze panel: full-width paste field with the navy primary action at its bottom-left. When a verdict lands it takes the row's position as a band-flooded banner: score as the hero figure in the band's ink, label beside it, band legend and coverage right.

**FORM.** Pinned by the user: light grey, major inspiration from the Palo Alto Networks site, tonal ramp over literal gradients, green/yellow-orange/red as good/warning/bad. Orange-as-brand withdrawn; green-as-brand rejected on measurement (see risk). No concept-seed roll ran and there is no seed key — a user-pinned direction beats the roll, and this was pinned in the request. Build path: code-led, so ambition lives in this block and the signature interaction below rather than in a comp. Signature interaction: when a verdict arrives, contribution bars draw in descending order of contribution and the flagged phrases sweep their highlight in after them, leading the eye score → factors → the exact words. Motion grammar: one orchestrated entrance, exponential ease-out from an already-visible default, nothing per-section and nothing repeated.

**Honest risk.** Green cannot be the brand accent. Status-good and a brand green sit ~9.7 ΔE apart — under the 15 floor where full-colour readers stop telling a pair apart — so green chrome beside a green verdict reads as "this is safe" when it means nothing at all. The same trap that ruled out orange. Mitigation: no brand hue; navy carries action, and green appears only where it genuinely means legitimate. Second risk: the triad is the classic deuteranopia pair, so the band never travels as colour alone — always colour plus its label plus its key mark. Yellow `#fab219` measures 1.68:1 on this plane and is therefore a fill and a chart mark only, never text.

**FINISH.** unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- Screenshot still pending; the grey ramp and band values above are measured and committed, and a reference image can still retune the greys.
- The risk score as a **meter** (single-hue track, band-coloured fill) versus the banner hero figure alone. A continuous green→amber→red gradient track is ruled out: a three-hue continuous ramp is the rainbow scale the viz rules forbid, and the bands are discrete states, not a magnitude gradient.
- Whether a phishing verdict should offer a recommended action (report / delete). The critique flagged its absence as the worst point of the emotional journey; it is design intent here, not a shipped capability.
- Roll-up tile counts can come from three `?label=` calls with no backend change, or one aggregate endpoint. Not decided.
