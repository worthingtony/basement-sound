# Hands-off jukebox (VirtualDJ)

**Status 2026-10-25:** design agreed. Network Control is on and the probe's `read` works against
VirtualDJ on the MacBook. **The gating question is answered: yes** - a script can put a chosen song
next in Automix (below). Nothing is built past the probe.

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

## Running the probe
Not during a party. Automix **on and playing** a short list named `ZZZ CLAUDE test`, and
VirtualDJ's browser on the main library, not a subfolder.

```
secret-run virtualdj -- python3 jukebox/vdj_probe.py read
secret-run virtualdj -- python3 jukebox/vdj_probe.py add "artist title"
```

claude-kit#82 merged 2026-10-25, so `secret-run virtualdj` works by name.
`add` leaves one song in the Automix
list; Tony deletes it. Also note what Automix does when its list runs out (stops or waits),
and whether `is_audible` answers - the TV page needs to know which deck is live.

### First `read`, 2026-10-25
Automix stopped, one song in its list. Deck 1 loaded, deck 2 empty, neither audible.
- `is_audible` answers `yes`/`no` - good for the TV page.
- Empty values (deck 2, Automix next) come back as `error:-2147…` strings, not blanks. The
  probe now treats them as empty; the service will have to as well.

### The gating question - answered 2026-10-25
`search "claude von stroke deep throat"`, then `browser_window 'songs'`, then `automix_add_next`
put Claude VonStroke - Deep Throat next in Automix while it played (list 3 -> 4, read back).
- **Focus matters.** The first try skipped `browser_window 'songs'`: the Automix list had focus,
  so `get_browsed_song` read *its* selection, and `automix_add_next` - which, per the verb list,
  moves a selected Automix song when Automix is active - added nothing. The probe reported a
  false YES because that song was already next; it now requires the list to grow.
- **Search is fuzzy, and the top hit can be a stream.** The three hits included library and
  Beatport results; the one selected was `netsearch://bp48803`. The service should check
  `get_browsed_filepath` against the guest's pick before adding, and decide whether guests
  may get streaming tracks (they need the connection and subscription up during a party).
- Automix mixed the added song in fine, by Tony's ear. Not tested yet: what happens when the
  list runs out.

### Volume levelling - to do
Songs arrive at different loudness, and nobody will be riding the gain. Read from
`settings.xml` on the MacBook, 2026-10-25 (nothing changed):

| Setting | Now | Note |
|---|---|---|
| `autoGain` | `auto` | What `auto` does versus `yes` still to look up |
| `automixRepeat` | `no` | The design needs the fallback list on repeat |
| `automixMaxLength` | `0` | No cap yet - the design wants one |
| `automixMode` | `smart` | |
| `writeHistory` | `yes` | ✅ |

Later layers, if autogain isn't enough: a VirtualDJ master limiter, then the DriveRack - the
mains limiter (`Limiter1`) is Off in preset #37 (see Design). No DriveRack change without Tony's OK.

## Service plan (draft 2026-10-25 - for Tony to agree)

### Decided (Tony, 2026-10-25)
| Question | Answer |
|---|---|
| Queue | **The service tops up Automix.** Remove-played stays on; the service keeps Automix 2-3 songs ahead (next guest pick by turn, else a fallback pick) plus ~10 fallback songs at the end as runway, so if the service dies the music plays on for ~40 min. |
| Song pool | **One curated VirtualDJ playlist, streams allowed.** 383 of the 442 library entries are streams (`netsearch://`), so a night needs the internet and the subscription up. |
| Turns | **First name on first pick.** Phones remember it (cookie); the kiosk asks every time. Round-robin across names. |
| Phones | **Mobile data, not Wi-Fi: a public URL on worthingtony.com**, QR on the TV. Infra documented in a homelab folder. |

### Shape
```
phone (mobile data) --https--> Cloudflare --tunnel--> cloudflared LXC (172.31.0.152)
                                                         |
iPad kiosk, TV (house LAN) ----------------------------> jukebox service (MacBook, :8765)
                                                         |  localhost only
                                                         v
                                              VirtualDJ Network Control (:8080)
```
- **Service:** Python on the MacBook, standard library only (like the rest of this repo, nothing to
  install). Holds the queue and guest names in memory plus a small JSON file so a restart keeps them.
- **Catalogue:** the curated playlist's songs, read from VirtualDJ (`database.xml` plus the playlist
  file in `MyLists`), with artist, title, BPM, key and file path. Guests search only this.
- **Adding a song:** `search "<artist> <title>"`, `browser_window 'songs'`, check
  `get_browsed_filepath` is the guest's pick (step down the results with `browser_scroll` if not),
  then `automix_add_next`, read back. One add at a time.
- **Pages:** guest (search, pick, see your place in line), kiosk (same, asks the name each time),
  TV (now playing, up next with names, QR). The TV updates with server-sent events.
- **Volume:** `autoGain` stays on; see Volume levelling.

### Public exposure - the part that needs care
- **Only the guest pages and their API go through the tunnel.** Network Control (`:8080`) stays
  off the tunnel; the plugin listens on every interface, so the service should be the only thing
  the tunnel can reach.
- **Party code.** The QR carries a code that changes each party; picks without it are refused, and
  outside party mode the service answers nothing but a closed page. Someone who kept the URL can't
  queue songs next week.
- **Limits:** per-name cap on queued songs, a Cloudflare rate-limit rule on the pick endpoint
  (Free plan allows it - see homelab `network/tunnel.md`), and no free text reaches VDJScript
  except artist and title from our own catalogue.
- **No Cloudflare Access** - guests have no login. The party code is the boundary.

### Infra (homelab, separate PR)
- New tunnel hostname (proposed `jukebox.worthingtony.com`) in the remotely managed tunnel, pointing
  at the MacBook.
- The MacBook needs a fixed address (DHCP reservation) and a firewall rule letting the cloudflared
  LXC (VLAN 1731) reach port 8765 on it (VLAN 1). Nothing else.
- When the MacBook is away or asleep the hostname just fails - acceptable.

### Build order
1. Catalogue reader + `add` by file path (CLI), proven against VirtualDJ.
2. Queue + top-up loop + fallback runway; run a night with no guests.
3. Kiosk and TV pages on the LAN.
4. Party code, limits, then the tunnel hostname and homelab changes.
5. Phase 2: fallback by BPM and key.

## Sources
- [VDJScript verb list](https://virtualdj.com/manuals/virtualdj/appendix/vdjscriptverbs.html)
- [Network Control plugin](https://virtualdj.com/wiki/NetworkControlPlugin.html)
- [Now Playing - Network Control setup, default port](https://nowplayingapp.com/help/guide/track-sources/virtualdj/)
- [VirtualDJ manual - Automix](https://virtualdj.com/manuals/virtualdj/interface/browser/sideview/automix.html)
- [VirtualDJ manual - Ask the DJ](https://virtualdj.com/manuals/virtualdj/interface/database/askthedj.html)
- [NoSongRequests - VirtualDJ settings](https://nosongrequests.com/virtualDJ)
- [VirtualDJ forum - stepping through the browser with playlist_add](https://virtualdj.com/forums/157026/Old_versions/Select_songs%3F.html)
