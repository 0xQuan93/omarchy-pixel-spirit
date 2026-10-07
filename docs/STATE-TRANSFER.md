# Carrying Wisp to another machine

Wisp's portable transfer is a single local JSON file. It contains fixed data
sections, never executable code or archive paths. No account or network service
is involved. The tool is in `plugin/state_transfer.py` in a repository checkout;
the development installer places it at the root of its flat installed plugin.

## Preview and export

From a repository checkout:

```sh
python3 plugin/state_transfer.py preview
python3 plugin/state_transfer.py export ~/Wisp-transfer.json
```

The default export includes **identity only**: Wisp's name, markings, chosen
lineage, interests, and local-model preference. It carries no growth journal,
room message, notes, chat, or settings. The preview prints only counts and
section names. Treat even an identity transfer as private.

For full companion continuity, explicitly select the other sections:

```sh
python3 plugin/state_transfer.py preview --sections identity,growth,room,settings
python3 plugin/state_transfer.py export ~/Wisp-continuity.json --sections identity,growth,room,settings
```

Growth history can contain filenames or project names, and room messages can
contain personal text. The machine's file/repository observation snapshot and
sampled-presence counters are left out of the export.
The export is created with user-only permissions and refuses to overwrite an
existing file.

Select any subset with `--sections identity,growth`, or explicitly include the
most personal material (room must be selected for notes):

```sh
python3 plugin/state_transfer.py export ~/Wisp-private.json --sections identity,growth,room,settings --include-notes --include-chat
python3 plugin/state_transfer.py inspect ~/Wisp-private.json
```

`--include-chat` includes recent conversation and the learned phrase bank. An
installed theme, plugin, or command still has to pass current validation before
a learned action can be proposed. The transfer does **not** include private
adapters, personal command aliases, the awareness diary, downloaded models,
generated command inventory, reminders, or screensaver integration. Copy or
reinstall those separately if desired.
Saved reviewed routines and the quick-action preference also stay on the source
machine; recreate routines only after checking the destination's controls.

## Import and recovery

Stop Wisp before applying a transfer, for example through Omarchy's **Setup →
Plugins → Disable** control. Wisp's normal helpers do not share the transfer
lock, so an active companion could write state at the same time. Inspect and
dry-run the import before applying it:

```sh
python3 plugin/state_transfer.py inspect ~/Wisp-transfer.json
python3 plugin/state_transfer.py import ~/Wisp-transfer.json
python3 plugin/state_transfer.py import ~/Wisp-transfer.json --apply
```

Use `--sections identity,room` to import only those sections. When notes were
excluded from the transfer, or `--skip-notes` is given, existing notes on the
destination stay in the room. Unselected files also stay untouched. The importer
validates the entire transfer and all selected state before any replacement. It
rejects unknown sections, duplicate JSON keys, oversized files, symlinks, and
malformed saved state. It never uses a path from the transfer as a filesystem
destination. The dry run lists files it would replace and any differing
identity name, earned XP, or room bond values, so review an older transfer
before applying it over newer progress.

An import resets the old machine's file/repository observation snapshot and
sampled-presence counters while preserving earned XP, traits, bond, and growth
history. This prevents old paths from being treated as new work. Imported
awareness and window-title consent, activity gestures, spoken replies, hidden
state, and screen coordinates start off; choose them again on the new machine.
Movement preference and command-tip preference carry over.

Before replacing files, Wisp retains their exact prior bytes in a private
`transfer-backup-*` directory in its state folder. It attempts to restore those
bytes if an import fails; a persistent disk failure can also prevent rollback,
in which case the error names the retained backup. A successful import prints
the backup path. Each file replacement is atomic, but the group of selected
files is not one atomic transaction. A process crash or power loss between
replacements can leave a mix of old and imported identity, growth, room, or
settings files. The pre-import backup is complete before the first replacement.
After stopping Wisp, inspect and restore that backup if the result is
incomplete:

```sh
python3 plugin/state_transfer.py restore /path/to/pixel-spirit/transfer-backup-XXXX
python3 plugin/state_transfer.py restore /path/to/pixel-spirit/transfer-backup-XXXX --apply
```

Restore validates the fixed backup inventory before writing and keeps a safety
backup of the state it replaces. The backup and exported JSON may contain
personal text; keep or remove them deliberately after checking the migrated
companion. Re-enable Wisp only after the transfer or restore is complete.

## Development install safety and host checks

`python3 install.py` builds a complete flat plugin in a staging directory
outside Omarchy's plugin discovery path. It retains existing user-owned
adapters, overlays the public files, checks Python syntax and manifest entry
points, and runs `omarchy plugin validate` when Omarchy is available. It then
switches the plugin directory and updates only Wisp's shell entries. If the
switch or configuration write fails, it restores the previous directory. A
successful update keeps that prior generation under
`~/.config/omarchy/.wisp-install-backups/`, outside plugin discovery. Wisp's
state directory is not replaced. Git-managed plugin installations should use
`omarchy plugin update` instead.
An installation carrying `.wisp-managed-overlay.json` belongs to a composed
local overlay; the public development installer refuses to replace it. Use the
overlay's own staged installer so personal controls and Wisp advance together.

`python3 install.py --check-host` is a read-only prerequisite probe. It checks
Python 3.11+, the Omarchy and Quickshell executables, the shell source, and
`shell.json`; it does not prove that every display, audio device, or third-party
adapter will work.

| Host | Status |
|---|---|
| Omarchy 4.0.4-1, Quickshell 0.3.1, Python 3.14.7 | Staging and plugin validation checked on 2026-10-07. |
| Older/newer Omarchy and Quickshell | Feature probe and runtime tests still needed. |
| Multiple physical monitors and non-default scaling | Still needs live validation. |

The stage validation is a pre-switch check, not a promise that a local private
adapter or a later Omarchy release has identical runtime behavior. Review Wisp
after shell reloads and use the retained generation for a manual rollback if a
runtime problem appears.
