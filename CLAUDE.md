# Basement Nightclub - sound system tuning

Tony's basement DJ system (separate from the upstairs home theater). Goal: sound as exquisite as the best club in the world.

## Working rules
- **No changes to the DriveRack without Tony's explicit OK.** Reading is always fine.
- **Back up before a session of changes:** `python3 venu360_backup.py` (read-only). Compare with `--diff backups/<file>.json`.
- **Read back every `set`** to confirm it took. Change one thing at a time so Tony can A/B by ear.
- Tony runs physical switches/knobs himself; ask him to.
- Tony prefers regular hyphens, not em dashes, in writing.

## Current state (2026-09-29)
- Loaded preset: **#37 "2026 Stereo Mains + Mono KSub Sub + Center"** (saved by Tony, unmodified). **#36** "Stereo Custom Mains + Mono KSub Sub auto eq" is the untouched original fallback.
- #37 = #36 plus two changes chosen by ear A/B:
  - QSC crossover (CrossoverIIR1 Sub band): high-pass **Out** (was 102 Hz - with the QSC's own 80 Hz low-pass it was nearly silent), low-pass Out.
  - QSC polarity (Sub_Polarity): **Inverted** (on Normal it partly cancelled the F1 subs; huge improvement).
- 812 tops EQ switched to **WITH SUB** (physical, preferred by ear).

## System as wired
| DriveRack out | Name | Feeds |
|---|---|---|
| 1 | Left Main | Left F1 Subwoofer (Input 2 in) -> its line out -> left Bose F1 Model 812 |
| 2 | Right Main | Right F1 Subwoofer (Input 1 in) -> its line out -> right Bose F1 Model 812 |
| 3 | Mono Sub | QSC KSub, own crossover at 80 Hz (Tony can change it) |
| 4 | Center Main | Center fill (model TBD), fed L+R sum; HP 50 Hz BW18, delay 0.69 ms, +2.9 dB, limiter on |
| 5, 6 | Output 5 / 6 | Unnamed, status unknown |

- F1 Subs: Line Output EQ **THRU** (Bose-recommended when feeding an 812 set to WITH SUB; HPF would double-filter), polarity NORM, volume ~4 o'clock.
- 812 tops: EQ WITH SUB, Signal Input LINE LEVEL, Ch 1 volume ~1-2 o'clock.
- Mains (outputs 1/2) run full range from the DriveRack; the F1 Sub/812 pairing handles their split.
- AutoEQ1 (mains room EQ, ON) has narrow +6 dB boosts (39.7 Hz Q12.4, 115/160/190 Hz, 399 Hz) - AutoEQ filling room nulls. Candidate to replace with measured cuts. All output PEQs, input PEQ, GEQs are off/flat.
- Measurement kit: miniDSP UMIK-2 with calibration file (use the 90° file, mic pointing up at head height on the dance floor). REW not yet confirmed installed.

## Roadmap
1. Optional ear test: QSC's own crossover (80 Hz vs higher). Re-check polarity after any crossover change; keep QSC volume constant while comparing.
2. QSC level trim by ear.
3. Measure with REW + UMIK-2: each group alone (mute outputs via DriveRack), then all together, several positions. Open questions: how the Mac feeds audio into the system; room size/surfaces/layout.
4. Tune: QSC delay vs F1 subs (REW acoustic timing reference, since USB mic has no loopback), levels, replace AutoEQ boosts with cuts, club-style target curve (lifted low end), center fill delay/level.
5. Placement, then room treatment, then hardware only if measurements show it's the limit.
6. Optional: rewire so tops, F1 subs and QSC each get their own DriveRack output.

## Files here
- `venu360_xover_ab.py` - `A` / `B` (QSC crossover 102 Hz/Out vs Out/Out), `normal` / `invert` (QSC polarity), `status`. Read-back verified; B auto-reverts to A on failure. Note: preset 37 already has B + Inverted.
- `venu360_backup.py` - read-only full dump to `backups/`, optional `--diff`.
- `backups/venu360_full_backup_2026-09-28_2312.json` - state of preset #36 before any changes (file name time is UTC; 6:12 pm local). Trustworthy.
- `backups/venu360_full_backup_2026-09-29_0528_preset37.json` - preset #37 after saving.
- `backups/venu360_config_snapshot.txt` - human-readable dump of #36.
- (On the Desktop, ignore `venu360_full_backup_2026-09-28_2307.BAD-misaligned.json` - values shifted by one block.)

## DriveRack VENU360 control protocol
Unit: 172.16.0.230, firmware 2.0.5.0, QNX-based.
- Plain-text commands over **UDP port 19272** (PA2-style protocol, but UDP). One command per datagram, newline-terminated. No login needed. TCP 19272 is refused.
- `get "\\Node\AT\Class_Name"` -> `"dbxDriveRackVENU360"`
- `ls "\\"`, `ls "\\Preset"` (blocks), `ls "\\Preset\<Block>\SV"` -> every parameter **with its value**, ends with `endls`
- `set "\\Preset\<Block>\SV\<Param>" <value>` -> `setr "<path>" "<formatted>"`. Confirmed: gains as numbers (`3` -> `"3.0dB"`), crossover freq numbers or `Out`, polarity `Normal`/`Inverted`.
- Output names: `ls "\\Preset\Output<N>\AT"` -> `OutputName`.
- Any set marks the preset `Modified` (`\\Node\Settings\SV\PresetIsModified`); reloading the stored preset reverts.
- **Reliability:** big blocks (AutoEQ curves) span several datagrams and can arrive late - match replies by the echoed path and read to `endls`; drain the socket first. `\\Node\Config\SV` never replies.
- Discovery: app broadcasts to 172.16.0.255:19272.

### Parameter tree
- Signal flow: In1/In2 -> A/B -> AutoEQ1 -> 2x3 crossover (CrossoverIIR1) -> outputs 1, 2 (mains band) and 3 (`Sub_*` params). Output 4 = A+B -> AutoEQ4 -> CrossoverIIR4 -> PEQOut4 -> Limiter4 -> DelayOut4. Outputs 5/6 = MidMixer5/6 chains. In3 -> InMixer3/GEQ3/PEQ3 path.
- Room EQ `AutoEQ1/4/5/6`: 14 bands `Band_N_Frequency/_Gain/_Q/_Slope/_Type`, `AutoEQ` On/Off.
- Output PEQ `PEQOut1/3/4/5/6`: 8 bands, `ParametricEQ` On/Off. Input PEQ `PEQ3`: 12 bands.
- Crossovers `CrossoverIIR1/4/5/6`: `Band_1_HPFrequency/HPType/LPFrequency/LPType/Gain/Polarity/Phase` (+ `Sub_*` on IIR1).
- Delay `DelayOut1/3/4/5/6`: `Delay`, `Amount`. Levels: `OutputGains` (`Channel_N_Gain/_Mute`), `ZoneGains`, `InputGains`.

## VENU360 Control app (Mac) gotcha
Won't connect when launched normally (2016 app never requests Local Network permission). Quit it, then launch from Terminal (keep the window open):
`APP=$(mdfind "kMDItemCFBundleIdentifier == 'com.harman.hsp.venu360'" | head -1); "$APP/Contents/MacOS/$(defaults read "$APP/Contents/Info" CFBundleExecutable)"`
The app may show stale values after a script change until reconnected. Its Virtual VENU360 doesn't answer network commands.

## REW API (for automated measurement)
REW has a REST(ish) API with webhooks. Start it from REW Preferences > API tab, or launch REW with `-api`. Swagger UI at `http://localhost:4735`; OpenAPI spec at `localhost:4735/doc.json` or `doc.yaml`. It's a work in progress - check the spec for implemented endpoints.
- Help: https://www.roomeqwizard.com/help/help/html/api.html
- Examples: https://github.com/audiomacgyver/rew-iqc (QC pass/fail), https://github.com/marionette609/rew-scripts (RTA measurements)
- Plan: drive REW sweeps via the API while muting/unmuting DriveRack outputs over UDP, so each speaker group (F1 stacks, QSC, center) is measured alone and together, then compute delay/levels/EQ and propose them to Tony before any `set`.
