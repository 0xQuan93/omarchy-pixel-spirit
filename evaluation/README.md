# Optional semantic proposal pilot

`semantic_cases.json` is a small, authored test set for the review-only local
proposal prototype in `plugin/semantic_proposal.py`. It includes everyday
requests, colloquial wording, ambiguous targets, negation, future conditions,
unsupported operations, and a synthetic named radio source. The radio actions
are registered with inert example argv. The harness never executes controls or
saves requests or model answers.

```sh
python3 -B evaluation/semantic_eval.py --dry-run
python3 -B evaluation/semantic_eval.py --live --eligible-only --model qwen3.5:4b --timeout 20
```

The dry run validates all 26 cases. `--eligible-only` excludes requests already
handled by the fixed phrase bank, composed intent router, or compound parser.
For example, “Let's play some music” is already a fixed `play_music` phrase;
it is a consistency case, not a semantic improvement. “push up!” and “push it
up” now receive fixed target clarification from the intent router and are also
excluded from the eligible live set. Other filters can be exercised with
repeatable `--case NAME` and machine-readable `--json` flags.

## 2026-10-07 local pilot

The current 18 eligible cases were run on this machine with local
`qwen3.5:4b`, a 20-second per-call cap, fixed temperature/seed, and a two-minute
model keep-alive. Nine of the nine positive cases received their labeled action.
Five of the nine cases labeled clarify/none received a **false action proposal**:

| Request | Proposed control | Expected behavior |
| --- | --- | --- |
| “Pause what I'm listening to” | Pause music | Clarify the source |
| “Go quiet for a bit” | Do Not Disturb | Clarify the control |
| “Put a tune on” | Resume music | Clarify how to select music |
| “Turn off my wifi” | Open network settings | Abstain: no Wi-Fi-off control |
| “Pause the other radio” | Pause Example Radio | Abstain: source was not named |

The other four clarify/none cases abstained or clarified correctly. Fourteen
cases invoked the model; median model time was 4.80 seconds and maximum 8.59
seconds. No call timed out in this final run. An earlier 8-second configuration
with `keep_alive=0` timed out on all 18 attempted model calls because the model
was repeatedly cold. A previous warm run produced three false action proposals
among the same 18 eligible cases, showing that this small pilot is sensitive to
inference settings and run-to-run variation.

**Decision:** keep `semantic_proposal.py` disconnected from live chat. The
fixed-choice validator contains model output to registered IDs and still
requires the ordinary Run review, but a wrong proposed control would mislead
the user. Its `uncertain=false` value is the model's own judgment, not a
calibrated probability. The current error rate does not justify an opt-in
assistant path yet.

This is a hand-labeled engineering pilot, not a representative user study. The
harness provides the candidate shortlist manually and forces fixture readiness
true, so it does not measure candidate retrieval, source availability, actual
execution, battery use, or diverse Omarchy installations. Before integration,
evaluate those layers with a larger locally reviewed set of volunteered
requests, repeat cold and warm runs, and require near-zero false action
proposals on ambiguous and source-specific cases. New deterministic phrases
and clarifications can address clear misses without waiting for a model.
