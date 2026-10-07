# Wisp roadmap for Omarchy

**Working proposal · October 7, 2026**

Wisp should be the familiar bridge between a person's request and Omarchy's real controls. A new user can learn one useful action and see what happened. An experienced user can combine trusted controls and understand the current machine without leaving their flow. The character and room give that utility a recognizable, lasting presence. Every claim about the machine should come from a named, fresh observation or a clearly labeled action receipt.

This roadmap builds on Wisp's existing local command bank, reviewed Run actions, four-step plans, native help, optional local conversation, persistent identity, room, and quiet awareness. The current [capability contract](CAPABILITIES.md) already separates a completed process, an accepted request, and verified state. The next work should make that distinction useful throughout the interface.

## Product principles

1. **Teach the native path.** Wisp explains the relevant Omarchy menu, shortcut, or setting as it helps, so people become more capable with their desktop.
2. **Show the strength of each claim.** A current reading includes its source and check time. An action says whether it was requested, accepted, verified, or unsuccessful. Unknown and expired readings stay visibly unknown.
3. **Keep agency with the person.** Ambiguous requests ask for a target. Reviewed controls remain the default; any faster path for low-risk, reversible actions is an explicit preference with the same receipt and current-state checks.
4. **Keep a familiar portable.** Identity, growth, and room history survive upgrades and machine changes through a selective, previewable transfer.
5. **Build on Omarchy's contracts.** Discover installed commands and plugin metadata for help; executable behavior comes only from reviewed Wisp capabilities and adapters. Optional local AI may interpret a bounded choice, while code owns validation, review, execution, and verification.
6. **Measure the cost of presence.** New observations and animation must respect quiet, battery, reduced-motion, privacy, and shell-performance budgets.

## Roadmap

The ranges show a sensible sequence after work begins, not release promises. Each milestone has a gate that can change its scope before the next begins.

| Horizon | Milestone | User-visible result | Release gate |
| --- | --- | --- | --- |
| 0–2 months | **Readable chat and first useful minute** | A responsive conversation panel, clear action receipts, and three optional first-task paths: navigate, personalize, or get help. | Short and long replies, choices, and plans remain readable with the composer and Run visible at 1366×768, 1920×1080, and 125–200% scale. At least four of five newcomers complete one chosen task without help within three minutes; four of five can tell whether Wisp verified its result. Core paths work without a model or awareness opt-in. |
| 2–4 months | **Current-state guidance** | Suggestions reflect whether a control is installed, connected, and actionable; a compact signal card explains each active source and its controls. | No playback suggestion appears without a controllable player and no microphone control is suggested without an available input. Every suggested action is checked again at Run. Unknown probes fail quiet within a bounded timeout. Primary flows work by keyboard and in reduced motion. |
| 4–6 months | **Portable familiar and safe upgrades** | Selective export/import, an optional “what changed” tour, and predictable behavior after Omarchy updates or display changes. | Fresh and prior-version round trips preserve identity, XP, bond, and chosen settings. Invalid imports leave existing state intact. A staged plugin update can roll back as a unit. Host-feature checks and a tested monitor/scale matrix determine what Wisp offers. |
| 6–9 months | **Omarchy guide and repeatable flow** | Help uses the installed desktop's command and plugin catalogue; users can save reviewed routines made of registered actions. | Each guide gives the native menu or shortcut as well as Wisp's path. Removed themes or plugins invalidate saved previews. A failed step stops later steps. In observed repeat tasks, at least eight of ten users need fewer interactions than their prior manual route. |
| 9–12 months | **Curated integration ecosystem** | A small, versioned adapter kit lets independently maintained Omarchy plugins expose named state and checked controls. An optional local semantic resolver is evaluated against real wording misses. | Two external adapters pass source-specific state and failure fixtures, plugin validation, QML checks, shell lifecycle checks, and removal checks. Disabled or incompatible sources fail closed. Semantic routing only selects from registered candidates, never executes from model output, and must outperform the fixed route on held-out everyday requests without unsafe false proposals. |

## Work inside the milestones

### 1. Readability and trustworthy results

The current chat is fixed at 360 px, with separate constrained scroll areas for replies, resources, choices, and plans ([Desktop.qml](../plugin/Desktop.qml)). Give the panel a display-aware maximum size and one primary reading area. Keep input and the current Run or Stop action visible. Short replies should shrink the reading area; long replies and plans should use the available screen height. The sprite, orbit, and restrained room artwork remain the visual anchors.

Replace the tiny route-only footer with a compact, expandable receipt: **source · checked time · requested / accepted / verified / unknown**. The current [machine reader](../plugin/machine_status.py) returns a sentence without a typed observation time; the [capability contract](CAPABILITIES.md) already provides action evidence levels. First define one bounded fact envelope with source, observed time, expiry, value or unknown reason, and evidence stage; then render it in chat and Commands. A user should be able to answer “Did it happen?” from the visible result.

Turn [Getting started](../plugin/SetupPanel.qml) into three small, optional task paths. Each path offers one installed action, previews the native route, and ends at a real result. Keep discovery counts and detailed privacy explanations available behind disclosure. Finishing a path must not switch on awareness, install a model, or change microphone settings.

Keep the room's calm composition, while explaining what rest, read, play, and garden change. Give its small mouse-target fireflies a keyboard-reachable equivalent. Check focus visibility and secondary-text contrast in stock light and dark themes as panel sizing improves.

### 2. Machine awareness that stays accurate

Separate **installed**, **connected**, and **actionable** in the capability registry. Today executable presence is the main availability check for several controls and [command hints](../plugin/command_hints.py); an installed player or microphone tool does not establish a live source. Add short, bounded, source-specific probes with explicit unknown states and a recheck before execution. Start with audio output/input and active media because users can immediately detect wrong claims.

Make each opt-in signal inspectable in Settings: what it reads, why, its last trigger, how long it is retained, and how to turn it off or clear it. Keep routine probes local and limited; measure their battery and shell cost before increasing cadence. Personal creative-tool and media integrations can use the same evidence shape without becoming assumptions in public Wisp.

### 3. Continuity across upgrades and machines

Current transfer requires copying the whole state directory while Wisp is stopped ([README](../README.md#persistence-and-recovery)). Add a versioned export with a preview of included identity, growth, room, settings, chat, and notes. Make chat and notes separately selectable, with a minimal identity-only default. Import validates into a temporary location, previews conflicts, then switches atomically while retaining a rollback copy. Hardware and source-specific bindings are revalidated on the destination.

Stage and validate a complete plugin generation before replacing the installed one. The current [development installer](../install.py) replaces individual files, which can briefly mix versions; personal overlays need the same generation check. Record a compatibility matrix for supported Omarchy, Quickshell, Python, display scale, and optional packages. Replace assumptions such as first-screen placement and exact upstream launcher text with feature probes or a clear unavailable explanation.

### 4. A useful guide and a responsible speed path

Omarchy exposes a [machine-readable command list](https://github.com/omacom/omarchy/blob/quattro/bin/omarchy) and a [plugin manifest contract](https://omarchy.org/manual/shell-plugins/). Use those as discovery sources for current help, alongside Wisp's existing curated explanations and discovered themes/panels. Catalogue entries can explain or propose a reviewed Wisp action; they do not grant new execution authority. Show the native shortcut or menu path where one exists.

Save frequent two-to-four-step routines as stable registered action IDs and arguments, with a concise preview, one Run, current target checks, and the existing stop-on-failure semantics. For experts who opt in, evaluate direct execution only for a small reviewed set of reversible, exact-target actions. A shared per-capability policy would keep public Wisp and personal overlays consistent while preserving review for uncertain targets and consequential actions.

### 5. Integration and common sense

Publish an adapter template with versioned fact and action schemas, source-specific fixtures, readback rules, expiry, error handling, and performance limits. Start with two willing Omarchy plugin maintainers. Manifests remain metadata; adapter code is reviewed, installed knowingly, and cannot gain authority from an arbitrary manifest string. Keep personal integrations in a separate overlay that passes the same contract.

Collect wording misses through voluntary, local feedback and a small regression corpus. Preserve the deterministic route for exact commands. If an installed local model helps, ask it a narrow typed question over a short list of registered candidates, including **none / ask which source**. It may prepare a proposal; the broker still validates and runs fixed code. Evaluate negation, quotation, conditional requests, stale context, multiple plausible sources, and no-model fallback before shipping. This follows the [code-owned typed-decision pattern](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) without requiring an external AI service.

## What to measure

- **Usefulness:** first completed task, weekly return by voluntary study, time and interactions for repeat tasks, and wording misses resolved without false proposals. Do not add default behavioral telemetry to obtain these numbers.
- **Truth:** false verified claims, stale readings presented as current, suggestions for absent sources, and how often users correctly understand a receipt.
- **Continuity:** export/import round trips, upgrade rollback, preservation of identity and earned history, and clean removal of an adapter.
- **Access and performance:** keyboard completion, panel clipping and contrast across light/dark themes and display scales, reduced-motion equivalence, idle CPU, battery cost, cold/warm response time, and shell recovery after a helper failure.

The first build slice is the responsive chat and typed receipt together. It gives every later feature a readable place to explain what Wisp knows, what it proposed, and what the machine actually did.
