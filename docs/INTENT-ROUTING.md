# Wisp 2.0 note

The intent layer below now participates in the shared [capability contract](CAPABILITIES.md). Explicit compounds and pending-plan edits run through their dedicated local planners before model fallback.

# Local intent interpretation

Exact phrases remain the first path for established commands. When those miss, Wisp can compose a request from a reviewed operation, named target, and supported qualifier. `intent_router.py` is a pure parser: it performs no I/O, inference, execution, or learning.

The existing percentage and installed-theme/plugin routes retain their typed validation. Reminder/creative/conversation paths retain their existing behavior when the intent parser has no complete match.

## Decisions

- **One supported interpretation:** return a local command preview. Run remains explicit, including in private overlays that execute exact phrases directly.
- **Missing target or competing interpretations:** return up to four fixed, labeled choices. Selecting one prepares Run; it does not execute.
- **Known target, unsupported operation:** explain locally and offer supported alternatives for that target.
- **Unknown target, timing, amount, source, or other unconsumed constraint:** do not silently strip it or execute the matching fragment. Normal conversation can handle the rest.
- **Unavailable tool:** report local unavailability. Do not retry the request through a model as if that could make the tool available.

Examples include “just open my clipboard,” “turn my speaker volume down one step,” and “close it.” The first two can produce explicit previews; the last asks which target. A private adapter can expose source-specific cartoon controls. “Close the cartoon controls but keep the video playing” maps to a hide action only when that adapter explicitly guarantees playback is preserved.

## Extending targets

Adapters supply bounded records with a display label, exact target aliases, and a mapping from canonical operations to registered fixed action IDs. Unknown IDs are dropped. Colliding aliases or competing parses produce clarification instead of selecting an arbitrary winner. The public module contains no machine-specific paths or commands.

Operation wording is separate from target vocabulary, so another safe target can reuse existing request forms without generating thousands of duplicate phrases. Every pattern consumes the whole request. Negation, quotations, conditional requests, unsupported compounds, and qualifiers have regression coverage. This is constrained command interpretation, not general language understanding.

## Interaction and privacy

Clarification choices live only in the current UI. Numbered choices accept exact ordinal replies such as “second one” or “2,” and exact labels; these prepare review locally. “Cancel” clears the options. “Yes” asks which option when several are visible; with one option it prepares Run. An exact “cancel” also clears a pending review locally. New requests, cancellation, errors, and panel transitions clear stale options. There is no autonomous alias learning, transcript mining, or inferred authorization from previous conversations. Action execution continues through the existing validated broker.

Parser, adversarial, broker integration, and native UI tests cover matching, availability, no-model/no-execution behavior, source distinctions, collisions, and clarification selection.
