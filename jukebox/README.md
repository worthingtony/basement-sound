# Hands-off jukebox (VirtualDJ)

**Status 2026-10-25:** design agreed. Network Control is on and the probe's `read` works against
VirtualDJ on the MacBook. **`add` (the gating question) not yet run.** Nothing is built past the probe.

## Goal
A TouchTunes-style jukebox for the basement: guests pick songs on a wall kiosk or their
phone, the songs play and mix, and nobody has to DJ. A TV shows now playing, up next and
a QR code. Runs on **VirtualDJ Pro on Tony's MacBook**.

## Why not an off-the-shelf request app
Every request service needs a person to click each song through:

| Option | Where requests land | Hands-off? |
|---|---|---|
| Ask the DJ (built into VirtualDJ) | Ask the DJ folder - right-click > Look Up, drag to a deck | No |
| NoSongRequests | Forwards into the same Ask the DJ folder | No |
| RequestSongs.co | Its plugin loads requests into the Karaoke tab, one click each | No |
| VirtualDJ karaoke mode | Plays a queue by itself, fills gaps with background music | Pauses between songs, doesn't mix |
| Juqed | Ready-made jukebox with QR, voting and Auto-DJ | Plays Apple Music, not VirtualDJ |

GeniusDJ, LiveFeedback and the 2026 AIPrompt folder suggest songs but never queue them.

## Design
- **VirtualDJ Automix does all playing and mixing.** It always holds a fallback playlist
  (shuffled, on repeat), so if the service dies the music keeps going.
- **A small service on the MacBook** reads VirtualDJ's library (`database.xml` - on the MacBook it is
  `~/Library/Application Support/VirtualDJ/database.xml`, not `~/Documents/VirtualDJ`), keeps the guest queue, and slots the next pick in with
  `automix_add_next` shortly before the current song ends. It talks to VirtualDJ through the
  **Network Control** plugin (Pro, VirtualDJ 2023+): HTTP `/query` and `/execute` running
  VDJScript, default port 8080, optional bearer password.
- **Kiosk:** an iPad locked to the service's page with iOS Guided Access. **Phones:** the
  same page through a QR code. **TV:** a page with now playing, up next and the QR code.
- **Rules:** guests pick from one curated playlist, not the whole library; turns go
  round-robin by guest; no repeats within a few hours.
- **VirtualDJ settings for unattended running:** `autoGain` on, `automixMaxLength` capped,
  `writeHistory` on.
- **Phase 2:** when the guest queue is empty, pick by BPM and key instead of the shuffled
  fallback.
- **Sound system:** the preset #37 backup (2026-09-29) has the mains limiter (`Limiter1`)
  Off; sub and center limiters are On. Worth deciding before nights nobody is watching.
  No DriveRack changes without Tony's OK.

## The gating question
The documented verbs add only **whatever is selected in VirtualDJ's browser** to Automix
(`automix_add_next`, `playlist_add`). The only verb found that takes a file path, `load`,
puts a song on a deck. So before any service code, `vdj_probe.py` checks:

1. Does `search "term"` leave the top hit selected?
2. Does `automix_add_next` then put that exact song next in Automix?

If not, try `browser_gotofolder` to a folder holding a one-song playlist. If nothing works,
Plan B is the service loading songs onto the idle deck itself with `load "path"` - it would
then own the mixing, a much bigger build. Ask Tony before going that way.

## Setup (Tony, at the MacBook)
- [x] **1Password:** new item `virtualdj-claude` in the **Agents** vault, field `credential`,
      type Password, generated **letters and digits only** (the plugin's `?bearer=` URL form
      would need symbols encoded). Notes: *Used by: Claude's jukebox probe, later the jukebox
      service on the MacBook. Copies: VirtualDJ Network Control plugin settings on the MacBook.*
- [x] **VirtualDJ:** Config > Extensions > Effects > Other > **Network Control** > Install.
- [x] **Turn it on:** Master panel > effect slot > **Auto-Start** > Network Control. It doesn't
      listen until this is on.
- [x] **Cog wheel:** port 8080, password pasted from 1Password - never into chat.
- [x] If macOS asks whether VirtualDJ may accept incoming connections: **Allow**.

Done 2026-10-25. The Master panel steps were followed from the wiki's wording, not screenshots.
Checked on the MacBook, values never printed: the item resolves (8 chars, letters and digits),
VirtualDJ listens on `*:8080` (every interface, not just localhost), and `/query` answers 401
without the password and 200 with it. Profile: claude-kit `virtualdj`
([claude-kit#82](https://github.com/worthingtony/claude-kit/pull/82)); record: homelab
`platform/credentials.md` ([homelab#96](https://github.com/worthingtony/homelab/pull/96)).
Still owed: the item's notes line.

## Running the probe
Not during a party. Automix **on and playing** a short list named `ZZZ CLAUDE test`, and
VirtualDJ's browser on the main library, not a subfolder.

```
secret-run virtualdj -- python3 jukebox/vdj_probe.py read
secret-run virtualdj -- python3 jukebox/vdj_probe.py add "artist title"
```

Until claude-kit#82 merges, pass `secret-run` that PR's `profiles/virtualdj.env` by path.
`add` leaves one song in the Automix
list; Tony deletes it. Also note what Automix does when its list runs out (stops or waits),
and whether `is_audible` answers - the TV page needs to know which deck is live.

### First `read`, 2026-10-25
Automix stopped, one song in its list. Deck 1 loaded, deck 2 empty, neither audible.
- `is_audible` answers `yes`/`no` - good for the TV page.
- Empty values (deck 2, Automix next) come back as `error:-2147…` strings, not blanks. The
  probe now treats them as empty; the service will have to as well.

## Sources
- [VDJScript verb list](https://virtualdj.com/manuals/virtualdj/appendix/vdjscriptverbs.html)
- [Network Control plugin](https://virtualdj.com/wiki/NetworkControlPlugin.html)
- [Now Playing - Network Control setup, default port](https://nowplayingapp.com/help/guide/track-sources/virtualdj/)
- [VirtualDJ manual - Automix](https://virtualdj.com/manuals/virtualdj/interface/browser/sideview/automix.html)
- [VirtualDJ manual - Ask the DJ](https://virtualdj.com/manuals/virtualdj/interface/database/askthedj.html)
- [NoSongRequests - VirtualDJ settings](https://nosongrequests.com/virtualDJ)
- [VirtualDJ forum - stepping through the browser with playlist_add](https://virtualdj.com/forums/157026/Old_versions/Select_songs%3F.html)
