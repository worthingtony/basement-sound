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
- **VirtualDJ Automix does all playing and mixing.** The service keeps its list a few songs
  ahead plus a fallback runway, so if the service dies the music plays on for a while
  (superseded the original "fallback playlist on repeat" - see Service plan).
- **A small service - an HA app, not on the MacBook, internal only (see Service plan)** - keeps the guest queue
  and slots each pick in with `automix_add_next`. It talks to VirtualDJ through the
  **Network Control** plugin (Pro, VirtualDJ 2023+): HTTP `/query` and `/execute` running
  VDJScript, default port 8080, optional bearer password. (VirtualDJ's library on the MacBook is
  `~/Library/Application Support/VirtualDJ/database.xml`, not `~/Documents/VirtualDJ` - but the
  app can't read it from the Pi.)
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
| `autoGain` | `auto` | Per the options list: sets each song to 0 dBA on load, or keeps a manual gain change. Kept |
| `automixAutoRemovePlayed` | `always` | Kept - the app tops the list up |
| `automixRepeat` | `yes` live | `settings.xml` said `no`, but VirtualDJ writes it only on quit - read live values with `setting '<name>'` through Network Control. Moot while remove-played is on |
| `automixMaxLength` | `480` | Set 2026-10-25 with Tony's OK (was `0`, no cap), read back |
| `automixMode` | `smart` | |
| `automixDualDeck` | `yes` | Set by Tony 2026-10-26 (was `no`, single-deck Automix). The aim: smoother levels at transitions. Read back live, `setting 'automixDualDeck'` = `yes`, with the next song preloaded on deck 2. The planner's `start` must then be 2 when the next song is already loaded |
| `writeHistory` | `yes` | ✅ |

Later layers, if autogain isn't enough: a VirtualDJ master limiter, then the DriveRack - the
mains limiter (`Limiter1`) is Off in preset #37 (see Design). No DriveRack change without Tony's OK.

## Service plan (agreed 2026-10-25)

### Decided (Tony, 2026-10-25)
| Question | Answer |
|---|---|
| Queue | **The service tops up Automix.** Remove-played stays on; the service keeps Automix 2-3 songs ahead (next guest pick by turn, else a fallback pick) plus ~10 fallback songs at the end as runway, so if the service dies the music plays on for ~40 min. |
| Song pool | **Two modes, switched per party on the admin face (Tony, 2026-10-25): Curated** - one VirtualDJ playlist Tony curates in VirtualDJ (the default); **Open + approve** - guests search everything VirtualDJ can search, and each pick reaches Tony as an HA notification with Approve / Deny; nothing plays until he taps. Optional filters on top (genres, a BPM band, a block list, sources). Streams allowed, so a night needs the internet. |
| Turns | **First name on first pick.** Phones remember it (cookie); the kiosk asks every time. Round-robin across names. |
| Name | **"Studio 841 Jukebox"** - the name VirtualDJ shows on its Remote accept list (Tony, 2026-10-25). |
| Plugin instead? | **No** (reviewed 2026-10-25): a VirtualDJ plugin's API is `SendCommand`/`GetInfo` - VDJScript, the same select-then-act limit - and a crash would take VirtualDJ down mid-party. Portability isn't a goal. |
| Where it runs | **An HA app on the Pi 5** (172.16.0.138). Nothing of ours runs on the MacBook - it only runs VirtualDJ. |
| Who reaches it | **Internal only, no public URL.** Guests join the guest Wi-Fi. A separate LXC for the request page is a later option, not v1. |
| Engine | **VirtualDJ (option A), not Music Assistant** - keep beatmatched Automix, driven by **posing as a VirtualDJ Remote** (add by path, proven 2026-10-25); Network Control as fallback. Every route into VirtualDJ checked 2026-10-25 shares the select-then-act model: Network Control, VirtualDJ Remote (skins run VDJScript), DJCEL's VirtualDJ-API-Python and VirtualDJ-MCP-Server (both thin wrappers over Network Control, GPL-3.0, must run on the MacBook). |
| Remote protocol | **Tony is OK reverse-engineering the VirtualDJ Remote phone app** - a time-boxed side quest, not on the build's critical path. See below. |

### Shape - one HA app, three faces
```
Tony ---------- HA sidebar (ingress) + MQTT entities --> admin face   \
kiosk iPad (house LAN) --------------------------------> request face  > jukebox HA app (Pi 5)
guest phones (guest Wi-Fi, VLAN 1922) -- one rule ----> request face  |
TV (house LAN) ----------------------------------------> /tv           /
                                                              | LAN, Bearer password
                                                              v
                                          VirtualDJ Network Control (MacBook, :8080)
```
| Face | Who | Reached through |
|---|---|---|
| **Admin** | Tony | HA ingress (behind HA login), plus entities on his HA dashboard via MQTT discovery (Mosquitto is already installed): party on/off, now playing, queue length, skip, block a name, "VirtualDJ reachable" |
| **Request** | kiosk iPad + guests' phones | The app's own port, **not HA**. The same page for both: the iPad shows it locked with Guided Access and asks a name each time; phones reach it on the guest Wi-Fi from a QR code and remember the name |
| **TV** | the TV | Same port, `/tv`: now playing, up next with names, two QR codes - join the guest Wi-Fi (standard Wi-Fi QR) and open the request page |

- **Guests never touch HA, not even on the kiosk.** HA has no per-entity permissions: a non-admin
  login still sees and controls everything (locks, cameras, Z-Wave). An iPad logged into HA in a
  party room is a remote for the house.
- **The app gets no HA or Supervisor API access** (`homeassistant_api` and `hassio_api` off). It
  talks to HA only by publishing MQTT. A bug in the request page then reaches the app's own
  container, not HA.
- **Request page closed outside party mode** - it answers only a "jukebox is off" page.
- **Delivered like Kitchen Scanner:** its own GitHub app repository in the HA app store, so it gets
  update notices - not a `local_` app copied by hand.
- **The VirtualDJ password** goes in the app's options (a new Copy on `virtualdj-claude`'s notes
  line, or its own `virtualdj-jukebox` item - per the credentials convention). Plain HTTP on the LAN.
- **MacBook asleep or away:** the request page says the jukebox is off; the admin entity shows
  VirtualDJ unreachable.
- **Health alert:** VirtualDJ unreachable for 30 s in party mode -> a notification to Tony (an HA
  automation on the MQTT entity).
- **Limits:** per-name cap on queued songs, and nothing a guest types reaches VDJScript - guests pick
  from the catalogue, and the app sends only that entry's own search terms.

### Adding a song - SUPERSEDED 2026-10-25 by the fake remote (below); kept as the Network Control fallback
Everything goes through Network Control's HTTP API. But **no VDJScript verb adds a given file to
Automix**: `automix_add_next`, `playlist_add` and `sidelist_add` add only the browser's selection.
Tested 2026-10-25: `automix_add_next "<file path>"` answered **HTTP 404 and added nothing**. Only
`load "path"` takes a path, and it loads straight onto a deck (the app would have to own the mixing -
Plan B, not wanted). **`browser_gotofolder "<path>"` doesn't work through the plugin either**: 404
and no move, for a real folder, the playlist's `.vdjfolder` file and the `mylists:/` form, with
single or double quotes; with no argument it answers `false` (2026-10-25).

So selection is by **search, then exact match** - for streams and files alike:
`search "<artist> <title>"`, `browser_window 'songs'`, `browser_scroll 'top'`, step with
`browser_scroll +1` until `get_browsed_filepath` equals the catalogue entry's path (`netsearch://…`
id or file path), then `automix_add_next`, then read the Automix list back. No exact match -> not
added, the pick goes back to the guest. One add at a time.

Someone clicking around VirtualDJ mid-add can still make an add fail - but not add the wrong song.

### Catalogue - probed 2026-10-25
With VirtualDJ's browser on the `ZZZ CLAUDE test` playlist (Tony opened it), `browser_window 'songs'`,
`browser_scroll 'top'` and stepping `+1` read all 3 songs, matching the playlist file
(`MyLists/ZZZ CLAUDE test.vdjfolder`) exactly:

| Path | Song | BPM | Key |
|---|---|---|---|
| `netsearch://ap6765480962` | Mr. V - Jus Dance (Remix) [Mixed] | 128.0 | Cm |
| `netsearch://ap6765480964` | Duice - The Pawee | 128.0 | G |
| `netsearch://ap6765480965` | Jonathan - Savage (Mixed) | 128.0 | A |

Properties: `bpm`, `key`, `length` (`03:21` form) work; `songlength` and `duration` don't. Nothing
was added (Automix count 4 before and after).

**Opening the playlist without the screen - found 2026-10-25.** Paths and favorite numbers don't
work through the plugin, but the folder tree can be stepped like VirtualDJ Remote does (its skins send
the same VDJScript):

| Try | Result |
|---|---|
| `browser_gotofolder "<path>"` (any form) | 404, no move |
| `browser_gotofolder 1` / `3` / `4` (favorite by number) | `false`, no move |
| Walk the tree from `top` with `browser_scroll +1` | ✅ reached the playlist in 59 steps - **but unsafe**: it steps through the online Beatport Charts folders, each loading from the internet, and the plugin stopped answering for several seconds. Never during a party |
| **Make the playlist the *last* favorite folder, then `browser_window 'folders'` + `browser_scroll 'bottom'`** | ✅ lands on `mylists:/ZZZ CLAUDE test.subfolders`, 3 files, in one step. Then `browser_window 'songs'`, `browser_scroll 'top'` and read |

So the app opens the catalogue itself: **folders, bottom, check `get_browsed_folder_path` is the
expected playlist** (refuse if not), then read. Rule for Tony: **the jukebox playlist stays the last
favorite** (`Folders/order` lists favorites in order; the playlist is last as of 2026-10-25).
The same move gets the browser back after anyone has clicked around.

(During the walk test the music was stopped - Tony had paused it; not caused by the probe.)

### Side quest - the VirtualDJ Remote protocol
*Goal: find out whether the phone app's connection can add a song by path, which Network Control can't.*

Seen 2026-10-25 (`lsof` on VirtualDJ, read-only): the only TCP listener is Network Control's `*:8080`.
UDP: `5353` (mDNS, likely how the Remote finds VirtualDJ), many sockets on `20808` (Ableton Link's
port - the Ableton Link plugin is installed), and ephemeral ports on the Wi-Fi (`172.16.0.70`) and
IoT (`192.168.21.73`) interfaces. **No Remote listener today** - it probably opens only once a Remote
is paired, or the Remote connects through VirtualDJ's servers ("accept list"). Unknown until tried.

Recon, in order, stopping at the first dead end:
1. Tony installs VirtualDJ Remote on a phone and pairs it (cost and licence unverified).
2. Read-only: `lsof` again - which new port, TCP or UDP, LAN or internet?
3. Tony runs a short `sudo tcpdump` on that port while pressing browser and add buttons on the phone.
4. If the payload is readable and shows VDJScript-like commands -> try the add-by-path forms. If it's
   encrypted or relayed through VirtualDJ's servers -> stop; option A stands.

My expectation: the Remote sends the same VDJScript, so no new capability - but cheap to check.

**Recon 2026-10-25 - the iOS Remote installed on the MacBook** (`/Applications/VirtualDJ Remote.app`,
`com.atomixproductions.VirtualDJRemote` 9.0.9618). Its code is FairPlay-encrypted (`cryptid 1`) and was
not decrypted. Read-only, from the unencrypted parts:
- **Its skin (`skin.zip`) drives everything with plain VDJScript**: `browser_scroll +1/-1`,
  `deck left load`, `automix`. The song list is a built-in `<browser>` widget.
- **The binary carries VirtualDJ's whole VDJScript verb table** (`automix_add_next`,
  `browser_gotofolder`, `playlist_add`, `sidelist_add`, ... in sequence) plus SQLCipher and OpenSSL -
  it is the VirtualDJ engine reshaped as a remote, so its link to VirtualDJ almost certainly carries
  VDJScript, likely encrypted.
- **No add-by-path verb exists in VDJScript**, so the Remote can't have one either - unless its
  `<browser>` widget uses a private message, which only watching a paired session would show.
(The Android APK route was dropped: the Remote is a paid app, APKMirror doesn't carry it, and other
mirrors would be unpaid copies. `jadx` was installed by Homebrew for it.)

**Breakthrough 2026-10-25 - the Remote protocol is plain text and HAS add-by-path.** With the iOS
Remote running on the MacBook and paired, `tcpdump` on `lo0` (no sudo - Wireshark's ChmodBPF gives
`access_bpf`) recorded a session while Tony browsed, searched and added a song.
- **Discovery:** the *Remote* advertises Bonjour `_vdjremote8._tcp` and **listens on TCP 4243**;
  **VirtualDJ connects to it** (LAN, not via VirtualDJ's servers). Only devices on VirtualDJ's
  accept list are used.
- **Framing:** every message is `"8JDV"` + uint32 LE total length + uint16 LE type + body.
- **Message types seen, Remote -> VirtualDJ:**

| Type | Body | Meaning |
|---|---|---|
| 1 | uint16 id, uint32, VDJScript text (`automix`, `deck left play_pause`) | register a VDJScript query/button under an id |
| 2 / 3 | id + value | press / update a registered id |
| 36 | uint16 flag, **folder path** (`mylists:/ZZZ CLAUDE test.subfolders`, `search://<term>`, `applemusic:`) | **list any folder or run a search by path** |
| 47 | flags, uint32 length, **song path** (`netsearch://…`, `search://…`, file path) | per-song info / artwork request |
| 49 | uint16, **VDJScript text with a path**: `mix_now "search://Cloonee/…"` | run a script |
| 50 | uint32, XML `<folderupdate path="playlist"><filedrop path="netsearch://ap6765480964" artist="Duice" title="The Pawee" … position="5"/></folderupdate>` | **add a song by path to the Automix list at a position** |

- VirtualDJ -> Remote (2.6 MB in ~2 min): state, folder listings and artwork - not yet decoded.
- The Automix list went from 4 to 6 songs during the session; Duice - The Pawee was added.

**What it means:** the jukebox app can **act as a VirtualDJ Remote** - advertise `_vdjremote8._tcp`
on VLAN 1, let VirtualDJ connect, and use type 36 (catalogue and search by path) and type 50
(add by path, at a position). **No browser steering at all.** Network Control stays as a fallback.
Risks: undocumented, could change with a VirtualDJ update; Tony accepts the app once in VirtualDJ's
Remote accept list.

**Handshake, recorded 2026-10-25** (Tony quit and reopened the Remote):
- **The port is not fixed.** The reopened Remote listened on 4244 (4243 was still held) and
  VirtualDJ followed the Bonjour advert; it also kept retrying the old port every 2 s. Follow the
  advert, never assume 4243.
- **No login, no encryption, no challenge.** VirtualDJ opens with two 120-byte type 43 deck-state
  blocks (floats) and type 54 skin settings (`vinylMode yes`, …); the Remote answers type 39 and
  type 64 `<info build="9618" skin="Default:4x3T" width=… />`, then asks for folders by path (type 36:
  `sidelist`, `sampler`, `playlist`, `karaoke`, root). VirtualDJ answers with **XML** (type 37):
  `<folderchildren path="" total="7">…<child name="Local Music" path="localmusic:"…/>` and
  `<foldercontent path="sidelist" … hasorder="yes" canmove="yes" candelete="yes">`.
- Button registrations (type 1) carry a 4-byte deck tag stored reversed: `tfel` = `left`, `hgir` =
  `righ`, then the VDJScript (`goto_bar 1`).
- **Accept list = device names.** `settings.xml` (written on quit, so stale) has
  `vdjRemoteDevices` = `Tonys iPhone`, `iRemoteDefaultPort` = 4243. A fake remote advertises its own
  name and Tony accepts it once. Name-based, so anything on VLAN 1 could claim an accepted name -
  acceptable on the house LAN, worth knowing.

**Proven end to end 2026-10-25 - `jukebox/vdj_remote_probe.py`.** The probe advertised
`ZZZ CLAUDE jukebox` (`dns-sd -R … _vdjremote8._tcp local. 4250`, built into macOS) and listened on
4250. Tony accepted it in VirtualDJ's Remote settings; VirtualDJ connected. Then, with no browser
steering at all:
- **Catalogue by path:** type 36 `mylists:/ZZZ CLAUDE test.subfolders` -> type 37 XML, all 3 songs.
- **Automix list by path:** type 36 `playlist` -> type 37, all songs with their paths.
- **Add by path:** type 50 `<filedrop path="netsearch://ap6765480962" … position="2"/>` -> Mr. V -
  Jus Dance landed at **exactly index 2**; Network Control agreed (count 6 -> 7).
- Type 37 replies are plain XML (`uint16 flag, uint32 1, XML`) or, when larger, **a zip holding
  `data.xml`** (`uint32 2`).
- The probe opens with only the type 39 hello; VirtualDJ then sends deck state (43), settings (54)
  and 59 unasked.

**So the app is a fake remote:** catalogue and Automix list read by path, picks dropped at an exact
position, now-playing from the deck-state messages (to decode). Network Control stays as a fallback
and for settings. The favorites trick and search-and-match are no longer needed.

**Now playing, decoded 2026-10-25.** Live state is *pushed*: the Remote registers VDJScript queries
(type 1: uint16 id, 4-byte deck tag stored reversed or zeros, script; then type 3 `uint16 2, uint32 id`
to subscribe) and VirtualDJ sends type 5 every time a value changes: uint16 id, a 4-byte type tag
stored reversed (`bool` uint32, `val` float32, `txt` uint32 length + UTF-8, `fail` = no value).
- **VirtualDJ numbers registrations from 0 in the order they arrive**, whatever id is sent.
- Through the Remote, `get_title` answers a yes/no and `get_time` answers nothing; use
  `get_title_before_remix` (what the real Remote uses), `get_artist`, `get_filepath`, `get_bpm`,
  `loaded`, `is_audible`, and `song_pos` (0..1) times the song's length.
- Checked live: deck 1 audible, Cloonee - Sippin' Yak, 118 BPM; deck 2 empty.
- VirtualDJ also pushes, unasked: deck-state blocks (43), skin settings (54), the loaded song as XML
  (55), cues (40), beatgrid (67), waveform (42) and cover art (44, JPEG) - the TV page can use the art.

**Build step 1 - done 2026-10-25; the app now lives in its own repo:
[worthingtony/studio841-jukebox](https://github.com/worthingtony/studio841-jukebox)** (public, so the HA
app store can install it - Tony, 2026-10-25). Version 0.1.0 ([PR #1](https://github.com/worthingtony/studio841-jukebox/pull/1)):
the protocol client (moved from `jukebox/app/` here), flow scoring (tempo + Camelot key), the
round-robin + flow planner, the service with an ingress status page, and autopilot (off by default).
15 unit tests; ran read-only from the MacBook.

**On the Pi, 2026-10-26.** Installed from the HA app store (repo added, built on the Pi from the
Dockerfile, slug `40cbc136_studio841_jukebox`) and started. Verified:
- the zeroconf advert: the Mac's `dns-sd` saw "Studio 841 Jukebox" and resolved it to `172.16.0.138:4250`;
- after Tony accepted it in VirtualDJ, VirtualDJ connected from `172.16.0.70` within seconds;
- `api/status` through ingress (the Supervisor proxy) showed deck 1 Cloonee - Sippin' Yak at 118 BPM,
  the 7-song Automix list, the 3-song test catalogue, and no error;
- the status port refuses anything but the ingress proxy (403 from the SSH app's container).

Seen in that Automix list: songs that came in as text (`search://Artist/Title/Remix`) carry no tempo or
key until VirtualDJ resolves them to a stream, so flow scores them neutral (0.5).

**The first hang, and 0.1.1 (2026-10-26).** At 08:21 one Automix read went unanswered. 0.1.0 treated
that as a lost connection and went back to waiting, but VirtualDJ still held the old one (`netstat` on
the Mac: ESTABLISHED, no traffic). Linux gave up on the socket after 15m51s (its retransmit limit), and
VirtualDJ didn't dial again until it next had something to send, an hour later. 0.1.1
([PR #2](https://github.com/worthingtony/studio841-jukebox/pull/2)) rides out failed ticks, drops the
connection itself after 5 in a row, and sets TCP keepalive. Cause not proven: it happened while a second
test remote (the Mac probe) was connected on the **same port number, 4250**. Since then the probe uses
4251, and the two ran side by side five times without trouble. After the update VirtualDJ reconnected
within a second: it dials again when the app closes cleanly.

**Removing a song: `<filedelete>` (2026-10-26).** The Remote app's binary names `filedelete` and `filemove`
(with `source_position`) beside `filedrop`. `<folderupdate path="playlist"><filedelete path=... position="N"/>`
took the two test songs (Duice, Mr. V) out of Automix, read back each time. The same message to a My Lists
playlist did nothing, so the extra Duice is still in "ZZZ CLAUDE test". `filemove` is untested.

**Song sources VirtualDJ lists** (children of `onlinemusic:`): CloudDrive, iDJPool, VJ'Pro, Digitrax,
Spotify, Apple Music, SoundCloud, Beatport, Offline Cache. Apple Music shows Playlists / Albums / Songs /
For You / Recently Added / Recently Played. Asking for Apple Music Playlists returned nothing within 10 s,
so it isn't proven. My Lists holds `party` (2 songs) and `ZZZ CLAUDE test` (3). The curated pool for the
autopilot test is **`party`**, which Tony is filling (2026-10-26).

**Search, checked 2026-10-25.** Type 36 `search://<term>` searches everything VirtualDJ can: for
`daft punk`, 402 results in three waves over ~2 s (0 -> 26 -> 127 -> 402, then an
`<updatedfolders>` notice) - 3 files, 25 `ap…` (Apple Music, by its separator), 100 `bp…` (Beatport),
274 `va…` (not identified - maybe VirtualDJ's video/karaoke catalogue). Results interleave
`separator://<Source>` headers and carry artist, title, genre and tempo. **Tempo in folder XML is
seconds per beat** (0.488 = 123 BPM). `folder()` now waits for the waves to settle and drops separators.
Registered queries are VDJScript in *query* context ("used as a LED mapping, it's a query" - VDJScript
wiki), so registering a script never runs it.

### Already installed that overlaps (checked 2026-10-25)
| What | Version | Overlap |
|---|---|---|
| **Music Assistant** (HA app) | 2.10.7, running | Same domain (music, queues, streaming providers) but it does not drive VirtualDJ. Not used in v1; Tony wants MA reuse later - decide then which one owns the queue |
| Mosquitto broker (HA app) | 7.1.2, running | **Used**, not overlapping: the app publishes its entities through it |
| Mini Media Player (HACS card) | v1.16.12 | Could show now playing on the dashboard. No conflict |

### Ideas from other jukeboxes and request apps (research, 2026-10-26)
A web survey: TouchTunes, AMI, Rockbot, Soundtrack, Festify, Spotify Jam, SharePlay, Jukestar,
WrzDJ, DJ Intelligence, VirtualDJ's Ask the DJ and karaoke, and DJCEL's MCP server. It was read
from docs and source where possible; vendor copy is marked as such in the agent's report. Top 8
to adopt, ranked:
1. **Energy (BPM) curve by time of night** for autopilot: warm-up, peak, wind-down (TouchTunes/Rockbot schedules, WrzDJ templates).
2. **Tie each name to a device** (cookie): typed first names make round-robin easy to game. **The kiosk is the hole:** a kiosk name matching a phone counts against that phone; unknown names get a kiosk-wide cap.
3. **Shuffle pick:** the guest names an artist and the planner picks that artist's best-fitting track (Rockbot).
4. **Artist-library mode:** open search auto-approves artists already in the curated list and asks only about the rest (Rockbot Smart Library). A third song-pool mode, with far fewer notifications.
5. **Event mode:** one HA switch pauses guest picks for a toast or Tony's own set (AMI).
6. **One-tap block** of a song or an artist, from the now-playing notification.
7. **Position and wait on the phone** ("#3, about 10 min"), and **recently played plus picker names** on the TV.
8. **Artist spacing:** no artist again within N songs.

Also worth weighing:
- **Refilling credits** (Jukestar) in place of a hard cap, spendable on a play-next bump, refunded when a pick is denied.
- **Dedications** shown on the TV.
- **"I'm leaving" removes my picks** (`filedelete` makes that possible).
- **A curated list of several hundred songs:** 15-20 an hour plus no repeats will exhaust a small list. `party` has 102.
- **Explicit flags are unreliable** across services. If we filter, decide whether the filter covers autopilot.
- **Check VirtualDJ's `automixTempoMode`:** "keep BPM" pitches up to ±10%, which interacts with the planner. Not checked.

Correction to the report: it says the ±6% tempo rule doesn't handle half and double time. `flow.tempo_score`
does (87 vs 174 BPM scores as a match). Not worth adopting: crowd voting on order (fights turns and flow),
tips, karaoke night, Ask the DJ (needs the internet, 100 requests, no per-user limits).
WrzDJ (MIT) has recommendation scoring worth reading before the guest step. Its AI assist calls an LLM,
so check which model before borrowing anything there.

### Improvements not yet decided
- **MacBook on Ethernet** and **Offline Cache** for the curated and fallback songs, so a Wi-Fi or
  internet blip isn't silence. (The MacBook also has an interface on the IoT VLAN 1921 as its
  default route - worth tidying.)
- **DriveRack mains limiter** (`Limiter1`, Off in preset #37) for unattended nights - Tony's call.
- **Request page in its own LXC** later, so guest Wi-Fi never reaches the Pi.

### Infra (homelab `jukebox/`)
- Firewall: **guest VLAN 1922 -> Pi, request port only** ([homelab#98](https://github.com/worthingtony/homelab/issues/98)).
  The app never calls the MacBook's :8080: VirtualDJ dials in to the app (2026-10-26). The 401 from HA
  in 0.09 s (2026-10-25) now matters for a different reason. It shows :8080 admits other hosts, and
  the MacBook's wired leg is on IoT 1921 (homelab `jukebox/README.md`).
- ~~DHCP reservation for the MacBook~~ - not needed (2026-10-26): VirtualDJ finds the app by Bonjour and dials in; the app never addresses the MacBook.

### Build order
0. ~~Probe: list the playlist~~ done 2026-10-25 (above). Still to prove: exact-match add of a search hit that isn't the top result.
1. ~~App skeleton~~ - done 2026-10-25: studio841-jukebox 0.1.0; on the Pi and connected 2026-10-26; 0.1.1 hardening the same day.
2. Queue + top-up loop + fallback runway **with flow ordering** (tempo, Camelot key, 2-slot fairness limit - Tony, 2026-10-25); planner and autopilot are in 0.1.0, a night with no guests still to run.
3. Admin face: ingress page + MQTT entities + health alert.
4. Request and TV faces on the house LAN (kiosk first).
5. Guest Wi-Fi rule; phones.
6. ~~Phase 2: fallback by BPM and key~~ - moved into step 2.

## Sources
- [VDJScript verb list](https://virtualdj.com/manuals/virtualdj/appendix/vdjscriptverbs.html)
- [Network Control plugin](https://virtualdj.com/wiki/NetworkControlPlugin.html)
- [Now Playing - Network Control setup, default port](https://nowplayingapp.com/help/guide/track-sources/virtualdj/)
- [VirtualDJ manual - Automix](https://virtualdj.com/manuals/virtualdj/interface/browser/sideview/automix.html)
- [VirtualDJ manual - Ask the DJ](https://virtualdj.com/manuals/virtualdj/interface/database/askthedj.html)
- [NoSongRequests - VirtualDJ settings](https://nosongrequests.com/virtualDJ)
- [VirtualDJ forum - stepping through the browser with playlist_add](https://virtualdj.com/forums/157026/Old_versions/Select_songs%3F.html)
