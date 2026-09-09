<p align="center"><img src="assets/preview.png" alt="Wisp — a local machine familiar" width="100%"></p>

# Wisp · a machine familiar

A native Omarchy companion that grows with the things you make. It roams your desktop, remembers a little context, keeps a pocket room, and dreams in your current theme. Every installation gets its own persistent markings and editable identity.

**No browser runtime. No cloud account. No mandatory AI.** Quickshell draws the companion; small Python helpers run when needed. Ollama supplies optional local conversation, naming, and room choices.

![Native dream room with sample identity and current theme](assets/dream-room.png)

*Dream-room preview uses sample state; no personal notes or identity are included.*

## Meet your familiar

- **Four evolution classes, sixteen silhouettes:** Forgewright, Prismweaver, Resonant, Lorekeeper.
- **A quiet desktop presence:** the orbital ring communicates mood and activity; names and status live in the popup.
- **An identity of its own:** age, name, personal influences, class selection, portable/stationary details, and exportable themed SVG portrait.
- **Roam, Follow, or Stay:** movement yields to dragging, hover, chat, and room interaction.
- **A pocket room:** nest, notes, fireflies, garden, local-AI activity choices, and bond-earned furnishings.
- **A native dream-room screensaver:** the same room and character, fullscreen across your displays, with Omarchy’s existing lock timing preserved.
- **Optional local chat and voice:** bounded desktop action proposals, seven-second offline dictation, and opt-in spoken replies.

![Four lineages and sixteen forms](assets/lineages.png)

## Request privacy

Wisp sends helper requests through an anonymous stdin pipe, never process arguments or environment variables. Each request is one newline-terminated JSON array, limited to 64 KiB including its delimiter. The helper rejects malformed frames, invalid command shapes, and legacy argv requests before dispatch. Chat, room notes, identity settings, speech, and saved state all use this channel; eSpeak also receives speech through stdin.

## Install

Requires **Omarchy Quattro with shell plugins**, Quickshell with `FloatingWindow.fullscreen` and AppId support, and **Python 3.11+**. Hyprland supplies pointer coordinates. Core play, identity, and evolution work without Ollama or speech packages.

```sh
omarchy plugin add https://github.com/0xQuan93/omarchy-pixel-spirit.git --enable
```

The bar’s small robot icon recalls the companion. If newly added QML components do not appear, run `omarchy restart shell`. This briefly reloads the shell.

For a development checkout, `python3 install.py` copies user-owned plugin files and updates only its entries in `shell.json`, backing up changes. The installer does not install packages, download models, or enable screensaver integration automatically.

### Optional local AI and voice

Run Ollama locally on `127.0.0.1:11434` and pull a suitable model, for example `ollama pull qwen3.5:4b`. In **Self**, enter another installed model if preferred. `PIXEL_SPIRIT_MODEL` overrides this setting. Model downloads are deliberately separate from plugin installation.

```sh
omarchy pkg add espeak-ng whisper-cpp
python3 ~/.config/omarchy/plugins/oxquan.pixel-spirit/tools/fetch_voice_model.py
```

The downloader fetches the pinned ~75 MiB English Whisper tiny model to `~/.local/share/pixel-spirit/ggml-tiny.en.bin` and verifies its SHA-256. It does not bundle the model into the plugin.

**Mic · 7s** records, counts down, transcribes locally, and puts text in the input for review. Press Send afterward. **Voice on** enables eSpeak NG replies. No passive microphone listening. Recognition quality depends on the microphone and tiny English model.

### Optional automatic dream room

First preview it from **Self → Preview dream room**. Any key, click, scroll, or pointer movement dismisses the screensaver after a short pointer grace period.

```sh
python3 ~/.config/omarchy/plugins/oxquan.pixel-spirit/setup_screensaver.py
omarchy restart shell
```

This explicitly clones the installed `omarchy.idle` service using Omarchy’s clone command, then changes only the clone’s screensaver launch command. It uses the existing `org.omarchy.screensaver` application ID, so Omarchy still observes window opening and dismissal. Lock timing, idle inhibitors, screensaver-off and stay-awake settings remain under Omarchy’s idle service. It refuses to overwrite an unrelated existing idle clone. No packaged Omarchy files are changed.

The clone should be reviewed after Omarchy updates because it is a user-owned copy. Automatic triggering honors **Stay awake**: turn that mode off through Omarchy when you want normal idle screensaving. This is a screensaver, not a replacement lock screen.

## Interact

| Gesture / control | Result |
|---|---|
| Single click | Open chat after the 400 ms multi-click window |
| Triple-click | Heart reaction and a daily pat reward |
| Drag | Reposition; roaming pauses for ten seconds |
| Right-click | Hide; recall from the bar |
| Self | Name, age, mood, class, influences, local model, portrait, screensaver |
| Name me | Local model chooses a name; rename again any time |
| Growth | Inspect observed work and earned XP |
| Room | Enter the pocket room; movement pauses while it is open |
| Drop text / `.txt` / `.md` | Add a small local note to the room shelf |
| Catch three sparks | Earn the daily firefly reward |
| Wisp chooses / Choose activity | Local model picks rest, read, play, or garden |

**Ring language:** idle breathes slowly; thinking uses a faster double orbit; working uses a bright segmented orbit; reading uses four alternating markers; playing scatters lively particles; happy uses bright markers and hearts; sleeping dims and stills the ring. Idle expressions are presentation, not background screen interpretation.

Room bond is separate from work XP. Pat, note, fireflies, rest, read, play, and garden each earn at most one bond point per local day. A plant unlocks at 3, a lamp at 8, and a crown at 16. No decay, hunger, streak penalties, or lost progress for resting. Automatic room choices never earn points.

## How it becomes yours

The first metadata scan establishes a starting character with **zero retroactive XP**. Thereafter, observed source/creative/writing-file changes and local Git-ref changes contribute capped growth. Auto class blends trait scores with chosen influences; manual class selection changes the lineage while preserving earned stage and XP.

| Influence | Class | Spark → Sprout → Familiar → Guardian |
|---|---|---|
| Maker | Forgewright | Rivet → Circuit cub → Forgewright → Iron aurora |
| Artist | Prismweaver | Dewdrop → Petal sprite → Prismweaver → Aurora manta |
| Musician | Resonant | Pulse → Echo fox → Resonant → Celestial ray |
| Archivist | Lorekeeper | Mote → Paper owl → Lorekeeper → Astral owl |

Stages unlock at **0 / 24 / 80 / 180 XP**. Random per-install markings persist across renames. Device personalization checks only whether a battery device exists; no serial numbers, machine IDs, biometrics, or hardware fingerprints are collected. An optional existing `USER.md` can seed explicitly mentioned music/art interests. You can change those influences in Self; they are aesthetic inputs, not personality diagnoses.

Default observation root is **`~/Work`**. Configure `PIXEL_SPIRIT_WORK` in the shell environment for another project folder; `PIXEL_SPIRIT_MEMORY` defaults to `<work>/Agent-Memory`. Without those folders the familiar still works and starts without a file-based imprint. Each installation uses only its own local state—no author memory or profile is shipped.

## Data, capabilities, and cost

- **Observation:** up to 16,000 entries, five directory levels and 32 repos per scan, with a four-second soft traversal budget; up to 1,000 shared-memory note metadata records. Dot directories, dependencies, builds, models, symlinks and this plugin’s source are excluded. Scans occur every ten minutes on AC, thirty on battery/power-saver; manual Growth scans have a one-minute minimum interval. Budget-limited scans are labelled.
- **Evidence, not attribution:** file changes earn 1 XP, HEAD changes 3, upstream-ref changes 2, capped at 24/day. These observations can include pulls, checkouts, clones or collaborator work. Upstream changes do **not** prove a push. No background fetch occurs.
- **Memory for chat:** bounded excerpts from optional `MEMORY.md`, `USER.md`, `Soul.md`, up to two filename-matched session notes, recent evolution metadata and up to three short room-note excerpts. These go only to local Ollama as fallible, untrusted context. The plugin never writes to the shared vault.
- **Controls:** explicit proposals for opening browser/terminal/files, volume, brightness, media playback, workspace navigation and power profiles. A Run button executes fixed argument lists. No arbitrary model-generated shell commands, deletion, publishing, or message sending.
- **Private state:** `~/.local/state/pixel-spirit/` (or XDG state root) holds identity, position, room, recent chat and evolution metadata. Chat Clear preserves identity/growth. Empty shelf deletes room notes. Notes are limited to 12 × 4096 characters. Temporary audio is removed after transcription. Local helper arguments can be inspected by other processes under your account.
- **Resources:** native rendering; short-lived Python helpers. AC motion ~30 Hz, battery ~10 Hz; sprite animation ~12.5 Hz, battery 4 Hz. Hidden animation stops. AI uses four threads on AC, two on battery/power-saver; keep-alive is two minutes AC and zero eco. Room AI chooses every three minutes AC / ten eco only while the room is open and otherwise idle. CPU inference can still take minutes and several GB of RAM. The dream room uses no AI inference.
- **Displays:** roaming and interactive panels use the first display; the screensaver creates one fullscreen window per display. Physical multi-monitor behavior has not been tested on the author’s one-display setup.

Plugins run with your normal user permissions in Omarchy’s shell. There is no network listener; the only routine network request is local Ollama chat. The optional model download is explicit. Artwork is original and generated from the shipped silhouettes.

## Commands and removal

```sh
omarchy shell pixel-spirit show
omarchy shell pixel-spirit hide
omarchy shell pixel-spirit reset
omarchy shell pixel-spirit identity
omarchy shell pixel-spirit room
omarchy shell pixel-spirit journal
omarchy shell pixel-spirit roam stay   # or roam / follow
omarchy shell pixel-spirit screensaver
omarchy shell pixel-spirit status
```

If you enabled the dream-room integration, restore its launcher **before** removing the plugin:

```sh
python3 ~/.config/omarchy/plugins/oxquan.pixel-spirit/setup_screensaver.py --remove
omarchy plugin remove oxquan.pixel-spirit
omarchy restart shell
```

The restored idle clone remains installed. The restore tool refuses to overwrite subsequent edits to it. Private companion state and the separately downloaded model are retained for deliberate cleanup. For a copied development install, use `python3 install.py --remove` instead of the plugin removal command.

## Development

```sh
python3 -m unittest discover -s . -v
omarchy plugin validate .
python3 tools/build_artwork.py
```

Tests cover action allowlisting, audio validity, evolution caps/deduplication, notes, bond, identity validation, persistence and all sixteen distinct silhouettes. Live checks covered Omarchy loading, local chat, room choice, self-naming, identity and room rendering, and native fullscreen screensaver launch/dismissal. Not every hardware/audio combination or long idle-to-lock transition has been tested.

Built by **0xQuan**. [MIT license](LICENSE). Model and speech-engine licenses belong to their respective upstream projects. [Omarchy plugin guide](https://omarchy.org/manual/shell-plugins/) · [Marketplace publishing guide](https://plugins.omarchy.org/publish.html).
