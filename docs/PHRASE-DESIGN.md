# Everyday command wording

The deterministic bank recognizes explicit requests for supported actions before model inference. It does not try to infer every possible intention. This pass adds 215 normalized public phrases across 77 existing actions, beyond the existing generated polite/gerund forms.

## Research and adaptation

Primary accessibility references reviewed September 16, 2026:

- [Google Voice Access commands](https://support.google.com/accessibility/android/answer/6151854?hl=en): explicit navigation, device and media requests, with disambiguation for unclear targets.
- [Microsoft Voice Access command list](https://support.microsoft.com/en-us/accessibility/windows/voice-access/voice-access-command-list): distinct commands for opening, switching and closing applications.
- [Apple Voice Control](https://support.apple.com/en-gb/guide/mac-help/mh40719/mac): discoverable command examples and separation between dictation and commands.

Our adaptation is to author familiar English descriptions, contractions, UK/US spelling, and small relative adjustments against Wisp's implemented catalogue. These references inform wording; they do not imply Wisp implements those platforms' entire command sets or supports every English dialect.

| Request | Fixed interpretation |
| --- | --- |
| turn the music down a bit | One volume-down step |
| bring up my folders | File manager |
| change the colour theme | Theme chooser |
| let me choose which speakers to use | Audio settings; user chooses the device |
| bring up my copy history | Clipboard picker |
| restore normal idle behaviour | Allow normal idle sleep |
| apply the Tokyo Night theme | Exact installed theme, revalidated before execution |
| show me the weather plugin | Exact enabled panel name, where the manifest supports opening |

## Boundaries and evidence

Whole utterances must match. Negation, quoted examples, conditional/delayed requests and extra actions remain unmatched. Complaints such as “I cannot hear” are not silently interpreted as unmute or volume-up. A toggle-only capability does not gain misleading on/off aliases. Unknown plugin names and arbitrary applications do not become executable targets.

`test_everyday_phrases.py` checks every authored request and systematically tests surrounding negation, conditions, quotations, delayed clauses and compound requests. `test_command_bank.py` verifies discovered targets, removal, collisions and unknown close/hide routes. Existing public Run confirmation remains unchanged.

Count is coverage evidence, not a claim of general computer control or language understanding. Add regression examples from real misses; check both phrase recognition and action receipts before assuming a model was called.
