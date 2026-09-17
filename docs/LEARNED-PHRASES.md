# Learned requests and local Omarchy help

Wisp 2.1 adds a private exact-request bank after its authored command, plan,
clarification, reminder, discovery and help routes. It saves new ordinary chat
requests when they reach model fallback; it does not import old chat history.

## Reuse and correction

A complete text reply becomes a **Saved local AI reply**, with its original date.
Repeating the request returns that snapshot before building model context or
calling inference. It is not refreshed machine state or a newly verified fact.
**Ask again** explicitly requests a fresh reply. **Forget phrase** removes the
entry; the next unknown request can be learned afresh. Both controls also appear
on the first learned result.

A model-selected action stores only its registered ID and capability fingerprint.
On reuse, the current registry supplies its label and checks availability and
fingerprint. Wisp returns a new Run proposal. It never replays a claim that an
action already completed, and learning never creates argv or grants execution
permission. This review requirement also applies to private overlays whose
built-in exact commands run directly.

Every attempt first records a pending generation. A failed, malformed, incomplete,
interrupted or short context-dependent result remains an unresolved entry with a
local explanation and retry controls. It cannot become a successful saved answer.
Deleting or refreshing a phrase prevents an older in-flight completion from
recreating it. State write failures leave the reply usable and explain when
learning could not be saved. A readable existing reply remains usable even if
updating its usage metadata fails.

## Boundaries and storage

Keys preserve case, punctuation, internal whitespace, negation and timing words;
only surrounding whitespace and canonical Unicode composition are normalized.
There is no fuzzy matching or silent removal of qualifiers. Existing authored
routes always win, so an upgraded built-in command can replace an older learned
interpretation.

Only plain text/emote or a fixed action ID/fingerprint is reusable. Model-created
resources, UI controls, plan tokens, choices, arbitrary commands, identity changes,
room decisions and scripts are never promoted into learned execution. Internal
room/naming requests and background inference are excluded; private film and
routine creation keep their explicit artifact workflows.

The local `learned-phrases.json` stores up to 512 entries, 4 MiB total, with a
4,000-character request and reply limit. Least recently used entries are evicted
when a bound is reached. Updates are locked and atomic, files are private, and
explicit deletion clears the recovery copy too. `show learned phrases` lists
recent requests; `forget all learned phrases` clears the bank. Clear chat clears
recent conversation separately. Nothing is synced, uploaded, or added to the
public phrase bank.

## Omarchy guidance

`omarchy_help.py` handles reviewed informational phrases for introduction,
getting started, documentation, shortcuts, themes, plugins, CLI and configuration.
Answers are written into the plugin. Resource buttons contain fixed official
manual links and named reference/configuration files that actually exist inside
an expected Omarchy root. User configuration contents are not read into replies.
Opening a resource requires a click; model-provided URLs never become buttons.
The online manual requires a connection, while installed references work offline.

Tests cover no-model repeated requests, registry changes, refresh/deletion races,
failed results, exact matching, bounds and backup recovery, private overlays,
inert native resource buttons, provenance and stale UI clearing. Physical voice
recognition and every third-party application remain ordinary-use checks.
