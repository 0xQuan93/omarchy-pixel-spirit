# Wisp 2.0 capability contract

Wisp resolves supported language into registered actions. The registry owns each
control's source, operation, plan eligibility, availability explanation, and
result evidence. The broker still owns execution. A phrase, model response,
plugin manifest, or saved plan cannot introduce executable code.

## Registered controls

`capability_registry.Registry` snapshots fixed argv and labels supplied by
reviewed application code. `capability_specs.build` registers portable Omarchy
controls; a private installation may supply additional reviewed metadata,
intent targets, and adjacent combination rules through the same contract.

Each action has:

- `sourceId` and `sourceLabel`: the device, application, or service affected.
- `operation`: the supported operation on that source.
- `planSafe`: whether it can participate in a reviewed multi-step plan.
- `verification`: `process`, `accepted`, or `state`.
- A current `available` value and an `availabilityReason` when unavailable.

Unannotated actions are single-command only. Unknown metadata fields,
unregistered actions, malformed targets, and cross-source combination rules
are rejected. The registry imports no adapters from manifest strings.

Availability establishes required software or a reviewed adapter check. It does
not guarantee that hardware is attached, a service is responsive, or an operation
will succeed. Runtime receipts remain necessary. Discovery separately checks
whether a plugin supports a native open route and is enabled.

## Discovery and source isolation

Installed themes and supported enabled panels gain typed `bank:` controls.
Percentage controls use bounded `param:` values. Only existing reviewed
resolvers construct their argv; manifest command fields and verification claims
are ignored. Every execution revalidates a discovered target. Multiple aliases
for one target cannot create multiple execution definitions.

Basic panel opening works automatically through the existing Omarchy manifest
contract. Richer playback, mute, or application-state controls require a reviewed
adapter implementation and registration. They are not inferred from a plugin's
name. A named player's mute must never fall back to system mute.

An adjacent recipe can combine a source's open-plus-mute into a verified muted
launch. Recipes cannot reorder intervening steps. Opposing states and conflicting
absolute settings for the same source are rejected. Focus-dependent operations
and unreviewed toggles remain individual commands.

## Evidence and outcomes

The normalized receipt has `ok`, `status`, `verification`, `sourceId`, `text`,
`route: local`, and an empty `action`.

| Evidence | Meaning |
|---|---|
| `process` / `completed` | The command finished successfully; downstream state was not independently observed. |
| `accepted` / `accepted` | The service or launcher accepted the request; opening or playback may still be pending. |
| `state` / `verified` | The reviewed adapter explicitly confirmed the requested state. |
| `failed` | The operation failed, returned an invalid receipt, or could not verify its promised result. |
| `cancelled` | The user canceled an operation; it is not a success. |

State adapters must return `verified: true` after a bounded readback. They cannot
claim it merely because a child process exited zero. Portable readbacks include
default-output/input mute, the selected power profile, and exact output volume.
Brightness percentage currently reports command completion rather than claiming
a verified display reading. Native app and panel launches report acceptance.

## Plans, edits, and recovery

A plan has at most four explicit steps and requires Run. All steps must resolve
before a preview is offered. The planner stores only action IDs, registration
fingerprints, a random token, and an expiry; it does not retain a transcript.

Plans expire after five minutes and can run once. A replacement preview receives
a new token. An update to a registered command's argv or metadata invalidates its
old preview. All required tools are checked before execution; runtime failures
still stop later steps. Accepted requests and completed commands are summarized
separately. Completed effects are not rolled back.

With a pending preview, examples of local edits are:

- `skip the browser` or `remove step two`
- `only set volume to 50%`
- `also open files`
- `replace step two with open terminal`
- `open terminal instead` when exactly one pending source matches

Ambiguous edits preserve the old preview. Removing its last step cancels it.
Unrecognized follow-ups stay local and ask for an edit or cancellation; they do
not accidentally execute a new command while a plan is awaiting review.

Progress tracks pending, running, accepted, completed, failed, and skipped steps.
Stop-after-step is cooperative: it prevents the next operation from starting,
but cannot undo completed work or interrupt every application's current action.
The cancellation decision and next-step claim are atomic. An execution lock
prevents concurrent plans from interleaving. A process identity check marks a
lost process interrupted; a restart never resumes or replays it.

## First run and upgrades

Getting started describes local commands, discovery, review, and settings.
Finishing it writes only its completion preference. It does not install a model,
enable awareness, enable title collection, or download software. Existing saved
identities suppress an automatic introduction; it remains available from More.

Existing growth metadata scanning and explicit room/identity behavior remain as
documented in the README; the introduction does not change those defaults.
Private machine adapters and earned identity remain separate from public code.

## Validation

The suite includes isolated imports without Omarchy, a model, or private modules;
temporary discovery roots; removed and disabled plugins; metadata injection;
percentage boundaries; source-state readbacks; edit/token lifecycle; cancellation,
process interruption and lock contention; and rendered native UI interaction.
Tests prohibit inference and effects for planning. These simulate clean systems;
they do not establish compatibility with every physical device or third-party
application. New adapters should add source-specific fixtures and failure cases.
