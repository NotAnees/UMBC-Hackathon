# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary: an everyday inbox owner.** Someone reading their own Gmail who wants to know whether a message in front of them is an attack. They are not a security professional, they did not go looking for a tool, and they meet the verdict inside the mail client they already use. For them the product surface is the Chrome extension's inline banner.

**Secondary: an operator.** The person running the detector — during the hackathon, a team member or a judge. They use the web console to analyze a message directly, review history, inspect why a score came out as it did, and mark verdicts right or wrong. The console assumes far more domain knowledge than the primary user has.

The split is load-bearing: terminology that is fine in the console (SPF, DKIM, DMARC, reply-to mismatch) is not automatically fine in the banner the primary user reads.

## Product Purpose

Tell someone whether an email is trying to attack them, and show the evidence for that answer. Success is a verdict the reader can check rather than one they must trust: the score is accompanied by the headers, links, and sentences that produced it.

A second, deliberate purpose is measurement — the system attacks itself with a red-team generator that plants known ground truth, so detection quality is a number the team can compute rather than a claim.

## Positioning

**The score shows its work.** Every number traces back to the exact header or sentence that produced it, and any factor the system could not measure is declared rather than quietly treated as safe. Comparable detectors return a verdict and, at best, a category label; this one returns the weighted factors, their individual contributions, the deterministic checks that fired with their evidence strings, and the phrases the AI pass objected to, quoted verbatim from the message.

## Operating Context

- The primary user meets the product inside Gmail, in a browser, mid-task, not in a security tool.
- The operator works in bursts: generate or ingest a batch of messages, then drill into individual verdicts.
- Demo conditions are a bright room and a projector, which is why the interface is light rather than dark.
- Four ingestion paths exist: the Chrome extension (Gmail API, `format=raw`), a server-side mailbox poller (Mailhog sandbox or a real Gmail inbox), direct paste, and `.eml` upload. Only the first two are automatic.
- The red-team service generates synthetic attacks into a local Mailhog sandbox; the detector ingests them through the normal path and its verdicts are joined back to planted ground truth.

## Capabilities and Constraints

**Confirmed capabilities**
- Parses raw RFC 822 messages, including pasted bodies with no headers at all.
- Scores on seven weighted factors summing to 1.0: AI deep scan 0.30, SPF/DKIM/DMARC 0.20, link-target mismatch 0.15, domain age 0.10, lookalike domain 0.10, From-vs-Reply-To 0.10, urgency language 0.05.
- Bands: legitimate 0–33, suspicious 34–66, phishing 67–100.
- Persists every email and verdict, with per-factor contributions and the AI pass's quoted spans, and accepts correct/incorrect feedback against a stored verdict.

**Constraints that future work must preserve**
- **Attacker-controlled content is never rendered as HTML.** Message bodies are displayed as text with highlight marks; no `innerHTML`, no unsandboxed iframe.
- **The red-team sender can only reach the local sandbox.** Its SMTP destination is hardcoded, with no parameter that accepts an arbitrary recipient or external host.
- **The AI pass is frequently unavailable** (API quota, model overload). Partial coverage is a normal operating state, not an error: missing factors are dropped and the remaining weights renormalised, never scored as safe.
- Gmail access is read-only (`gmail.readonly`); nothing sends, modifies, or deletes mail.
- The red-team generator is deliberately template-driven, not LLM-driven, despite earlier planning documents describing it otherwise.

**Known debt, explicitly recorded rather than hidden**
- No database migrations; schema comes from `create_all`, so column additions have required wiping the volume.
- No seed corpus, so the app starts empty.
- No committed automated tests.
- The backend Gmail poller's one-time OAuth consent has not been run.

## Brand Commitments

- The console presents itself as "Phish".
- The user pinned a light interface and named the Palo Alto Networks site as the visual reference. Recorded as given; the visual system itself lives in DESIGN.md.

## Evidence on Hand

- **Real ground truth**: the red team stamps each generated sample with an id and stores its true label, difficulty, and planted tells, so catch rate and false-positive rate are computed against an answer key rather than asserted. Observed in-session runs reached 10/10 and 7/7 phishing caught with no false positives; these are development observations, not benchmarks.
- **Feedback records** on stored verdicts, available for an agreement-rate metric.
- **Absent, and not to be fabricated**: no external corpus (PhishTank/Nazario/Enron were planned, never loaded), no customers, no third-party evaluation, no performance benchmarks, no pricing or deployment claims.

## Product Principles

1. **Show the evidence, not just the verdict.** A number the reader cannot check is worth less than a slightly worse number they can.
2. **Declare what was not measured.** An unmeasured factor is never reported as safe; coverage is stated in the interface.
3. **Two audiences, two registers.** The operator's console may use security terminology; the banner an everyday inbox owner reads may not.
4. **Degrade rather than fail.** Any layer can drop out — AI quota, Gmail auth, the sandbox — and the product still returns a usable, honestly-labelled answer.
5. **The adversary is in-house and contained.** Attack generation exists to measure the detector, and its only destination is the local sandbox.

## Accessibility & Inclusion

No external standard was mandated by the user. WCAG 2.1 AA has been adopted as the working floor and is enforced by measurement: every text token is checked against its actual surface, interactive controls carry visible focus indicators, tables carry real headers, async states and errors are announced, and a verdict never travels as colour alone — always colour plus label plus key mark, because the green/amber/red triad is the common colour-vision-deficiency pair.

## Open Decisions

- **Lifespan**: built as a hackathon demo, but to be treated as if it will continue in use. Throwaway shortcuts should be recorded as debt (above) rather than accepted silently.
- Whether a phishing verdict should offer a recommended action (report, delete, do-not-click). Currently it diagnoses and stops.
- Whether the red-team service ever becomes LLM-driven; it competes for the same API budget as detection.
