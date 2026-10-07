# Reviewed Wisp adapter contract

Wisp can give a named Omarchy source its own controls and verified state. An adapter is **reviewed Python application code** installed alongside Wisp. A plugin manifest, discovered name, saved phrase, or model answer never defines executable behavior. Omarchy plugins run with the user's permissions inside the shared shell; review their code before enabling them. See the [Omarchy plugin contract](https://omarchy.org/manual/shell-plugins/) and Wisp's [capability contract](CAPABILITIES.md).

## Version 1 control specification

`plugin/adapter_contract.py` validates a bounded source specification and returns the three maps accepted by `capabilities.registry(extensions=...)`. The caller writes fixed argv and labels in source code. It must not build this specification from a plugin manifest or user text.

```python
from adapter_contract import extension

actions, labels, metadata = extension({
    'schemaVersion': 1,
    'sourceId': 'example.radio',
    'sourceLabel': 'Example Radio',
    'controls': [{
        'id': 'example_radio_pause',
        'label': 'Pause Example Radio',
        'argv': ['example-radio-control', 'pause'],
        'operation': 'pause',
        'planSafe': False,
        'verification': 'state',
    }],
})
```

Register only controls that the adapter actually implements. A `state` control returns `verified: true` only after a bounded source-specific readback confirms the requested state. The registry marks a missing or failed readback unsuccessful. `accepted` means the source accepted a request; `process` means a command finished. Neither implies the downstream state changed. Do not substitute a global audio or system control when a named source is unavailable.

The control runner remains Wisp's reviewed broker. The adapter can add fixed actions and metadata, but it cannot grant itself a Run bypass, arbitrary shell input, or authority from discovered metadata. A named source should use its own installed/connected/actionable probe with a short timeout and a fresh check when Run is pressed.

## Version 1 fact envelope

Use `validate_fact(fact, expected_source)` for an on-demand observation. `observedAtMs` and `expiresAtMs` are Unix milliseconds, with a maximum 60-second lifetime. A verified fact has a bounded JSON `value` and empty `unknownReason`; an unknown fact has no value and a clear reason. The validator returns the display-safe evidence fields, without the raw value.

```python
from adapter_contract import validate_fact
import time

now = time.time_ns() // 1_000_000
fact = {
    'schemaVersion': 1,
    'sourceId': 'example.radio',
    'sourceLabel': 'Example Radio',
    'observedAtMs': now,
    'expiresAtMs': now + 5000,
    'status': 'verified',
    'verification': 'state',
    'unknownReason': '',
    'value': {'playing': True},
}
evidence = validate_fact(fact, 'example.radio', 'Example Radio')
```

The caller formats user-visible prose from the checked value and attaches `evidence` to its Wisp reply. If the source disappears, times out, or returns a malformed reading, return an unknown fact. Do not replay an old value as current. The envelope is at most 16 KiB and cannot include arbitrary extra fields.

## Adapter review checklist

1. Confirm that source identity and action targets are exact. Disabling or removing the source makes actions unavailable.
2. Bound every read and execution timeout. A source failure gives an unknown or failed receipt and never blocks the shell indefinitely.
3. Test closed, paused, active, stale, unreadable, and changed-between-preview-and-Run states.
4. Test source isolation: one player's pause or mute never changes another player or system output.
5. Validate the plugin manifest and QML, then test enable, disable, update, shell reload, and removal on supported Omarchy versions.
6. Measure idle and active CPU/battery cost. Prefer event-driven or on-demand facts over an always-running poll.

`test_adapter_contract.py` includes two independent source fixtures, malformed specifications, source isolation, and verified-versus-unverified receipt checks. A real external adapter still needs an independently maintained implementation and live lifecycle test before Wisp can claim ecosystem coverage.
