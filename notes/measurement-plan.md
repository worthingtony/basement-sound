# Measurement and tuning plan (DRAFT - not agreed yet)

Status 2026-09-29: plan only. Nothing here has been run. Every DriveRack `set` (including mutes) needs Tony's OK per session.

## BLOCKED 2026-09-29: UMIK-2 (serial 8111561) is faulty
Enumerates fine (USB 2.0 high speed, 48 kHz, macOS input volume 100) but passes only ~34 dB SPL of self-noise - no response to claps or a loud sweep. Same result through the dock/repeater, plugged directly into the Mac (macOS Sound input meter flat), and on Tony's iPhone. Re-flashing firmware v2.06 didn't help. So every REW test that day was mic noise; the 34 dB "quiet room" reading was never the room.

Everything else was proven working that day: REW 5.40 beta 135 with a Pro licence (API sweeps start, settings apply), DJM-250MK2 as REW output (sweep audible in the room), cal file, BlueRigger repeater path. Resume at Session 0 with a working mic.

## What's verified so far
- REW **5.40 Beta 120, API 0.9.4**, running on `localhost:4735`. API has what we need: `measure` (sweeps, acoustic timing reference), `alignment-tool` (sub delay/polarity), `eq` (house curve, match target), `measurements/{id}/rt60`, `spl-meter`, `generator`.
- REW input: **UMIK-2**, cal file `cal/8111561_90deg.txt` (the 90° file - correct for mic pointing up; serial 8111561). REW points at the repo copy ("Input cal processed", 2026-09-29).
- REW sample rate is **48 kHz** (changed when the UMIK-2 was reselected, 2026-09-29; macOS agrees).
- REW timing reference is **None** - change to Acoustic.
- REW output is "Default Device". The DJM-250MK2 wasn't connected on 2026-09-29, so whether the Mac sees it without Pioneer's driver is still unchecked - first job of Session 0.
- **REW API without a Pro licence (tested 2026-09-29):** GETs work; output device/channel and input device/cal can be set. Refused with "A Pro upgrade license is required": measure level, sweep configuration, protection options, naming, and **starting a measurement** (`/measure/command SPL`). So sweeps are started by hand in REW's window unless Tony buys Pro (roomeqwizard.com/upgrades.html; one-time, per user).
- Gotcha: selecting the REW **output** device resets the **input** to "Default Device" and clears the cal. Always set output first, then input + cal, then read both back.
- REW has no dbx EQ profile; use "Generic" / "Configurable PEQ" and translate filters to DriveRack PEQ bands by hand (script).

## Signal path
Mac -> USB -> DJM-250MK2 (one channel, input set to USB) -> master out (**balanced XLR**, per Tony) -> DriveRack In A/B -> outputs 1-4.

DJM must be a fixed, known, flat stage for every measurement:
- Channel EQ at 0 (centre detents), Sound Color FX off, crossfader not cutting that channel, channel fader and master at marked positions, trim noted.
- Photo of the mixer settings goes in `measurements/<session>/`.

## The crossover question: DriveRack or KS212C?
Tony's preference: **DriveRack**. The KS212C limits how far that can go.

What the KS212C manual says:
- Its low-pass is **80 Hz or 100 Hz - there is no bypass/thru**, so there is always one filter in the sub itself. Currently 80 Hz.
- It has its own delay (0-100 ms). Keep it at **0** and do all delay on the DriveRack (`DelayOut3`), so there's one place to look.
- Loop-thru outputs are unprocessed, so it can't high-pass anything downstream.
- It's a fixed cardioid (15 dB rear rejection at 70 Hz): front toward the floor; rear rejection means less bounce off the wall behind it - matters for placement later.

Options:
- **(i) As now:** KS212C at 80 Hz is the crossover, DriveRack `Sub_LPFrequency` Out.
- **(ii) DriveRack owns it (as far as possible):** KS212C set to **100 Hz** as an outer filter (least interference), DriveRack `Sub_LP` sets the real crossover at or below ~80 Hz, with a slope we choose. Two filters in series near 100 Hz, but that's fine: we align on the **measured** acoustic response, which includes both.
- Recommendation: (ii), compared against (i) by measurement. Keep whichever integrates better with the F1 subs.

Bigger picture: the F1 subs get full range and split to the 812s with their own fixed internal crossover, so the KS212C isn't really "crossing to tops" - it **overlaps** the F1 subs. The real choice is:
  - (a) KS212C and F1 subs share the same bass band (more headroom; needs delay + polarity alignment - current setup), or
  - (b) KS212C low-passed lower (e.g. ~60 Hz) to reinforce only the deepest band.
  Measurement decides. Roadmap item 6 (separate outputs for tops/F1 subs/KS212C) would let the DriveRack own every crossover - worth revisiting after this.

Subsonic high-pass (~30 Hz) on the DriveRack sub output: the KS212C is already -10 dB at 39 Hz, so this mostly keeps useless deep content out of its limiter. Measure with and without.

Center (JBL EON610): -10 dB at 52 Hz, but the DriveRack high-pass is 50 Hz BW18. At club level the 10" is being asked for bass it can't make, while the subs already cover that range. Candidate: raise it to ~70-80 Hz. Measure first.

## Timing without loopback
USB mic = no loopback, and the DJM and UMIK-2 run on different clocks. Use REW's **acoustic timing reference**:
- Ref played on **L**, measurement sweep on **R**. Left stack (output 1) stays on as the "clock" for every measurement (agreed with Tony 2026-09-29).
- Group under test is fed from R; DriveRack mutes the rest:

| Measure | Out 1 (L stack) | Out 2 (R stack) | Out 3 (KS212C) | Out 4 (Center) |
|---|---|---|---|---|
| R stack | on (ref only) | **on** | mute | mute |
| KS212C | on (ref only) | mute | **on** | mute |
| Center | on (ref only) | mute | mute | **on** |
| All | on | on | on | on |

- KS212C gets L+R, so it also receives the ref, but the ref is high-frequency and its low-pass rejects it.
- The center is muted for every measurement except its own, so it only matters then: **when the center is the one under test**, it gets L+R and plays the ref as well as the sweep - two ref arrivals. Options, in order:
  1. Dry run: see whether REW still locks on cleanly (the two arrivals are only ~1 ms apart plus distance).
  2. Find a DriveRack crosspoint that feeds output 4 from B (R) only for that one measurement. Not found yet - `MidRouter4` only exposes a master gain/mute; look in the app's routing screens.
  3. Fallback: take the center's magnitude response with no timing ref, and set its delay by ear/impulse from an all-on measurement.
- Left stack alone: mirror image (ref on R, right stack as clock) - or check whether REW allows ref and sweep on the same channel.

## Mic positions
Tony: "as many as we need" - the spread is what makes room-treatment needs obvious.

- Mic at standing head height (~1.6-1.7 m), pointing straight up, 90° cal file.
- **Room sketch first:** dimensions, speaker positions and heights, a grid on the floor. Every measurement name carries its grid reference.
- **Two tiers**, so the session stays manageable:
  - **Core spots (~6):** 5 on the dance floor (centre + 4 around it) + DJ booth. Every group alone + all on. These drive the tuning decisions.
  - **Grid (~1 m spacing, the whole floor plus anywhere people stand or sit):** all on only. These drive the treatment decisions.
- What the grid shows:
  - Big spot-to-spot swings below ~300 Hz = room modes -> sub placement and bass traps.
  - Long decay (RT60/waterfall) in a band -> absorption needed there.
  - Strong early spikes in the impulse (ETC) at a spot -> a first-reflection surface worth a panel.

### Laptop logistics
Tony will move the laptop with the mic (no long USB-C cable). Two catches:
- **The laptop also drives the DJM over USB.** If it moves around the floor, that cable has to reach too - it's the same problem at the other end.
- **The laptop body reflects sound** into a mic right next to it. Keep it low (floor or a low cart), well below and behind the mic, never between mic and speakers.

**Resolved 2026-09-29: Mac -> dock -> BlueRigger 10 m USB 2.0 active repeater -> USB-C to USB-A data cable -> UMIK-2.** Laptop stays at the booth next to the DJM; only the mic moves. Earlier failures were all cables without data lines, not the repeater. 4 min listen-only test through the repeater: no disconnects, no REW errors. Not yet proven: glitch-free sweeps (REW reports those during a measurement) - check in Session 0.

Better option: a **5-10 m active USB extension for the UMIK-2**, so the laptop stays at the booth next to the DJM and only the mic moves. Cheap, and it removes both catches. Unverified: that the UMIK-2 runs reliably on one - test in Session 0.

## Levels and safety
- Capture noise floor first.
- Sweeps start low; working level ~85 dB C at the centre spot. One short pass at party level (tuning depends on level - see ASR notes). Hearing protection for that pass.
- REW generator protection on; subs watched for over-excursion.
- All mutes go through a script that reads back every set and **restores on exit, including Ctrl-C** (fallback: reload preset #37).

## Sessions
**Session 0 - dry run (no DriveRack changes except the optional mute in step 2):**
1. Setup: DJM visible to the Mac, REW at 48 kHz, output = DJM, UMIK-2 on the active extension if we got one.
2. **Signal-chain check** (DJM master XLR -> DriveRack In A/B, balanced):
   - Confirm the DriveRack inputs are on analog, not AES (read-only: `AESCh12Input` / `AESCh34Input`).
   - **Clip check, speakers protected** - DriveRack outputs muted (needs Tony's OK) or amps/powered speakers off (Tony). REW pink noise into the DJM channel, DJM channel fader and master up to full: does the DriveRack input meter clip? If it does, mark the DJM master's safe maximum.
   - **Operating level:** with a loud mastered track at Tony's normal DJM master position, DriveRack input peaks should sit roughly 6-10 dB below clip. Too low = raise the DJM master and trim the DriveRack outputs down; too hot = the reverse.
   - Meters: read them in the VENU360 app or on the front panel. Unverified whether they can be read over UDP (`\\Node\DA`?) - check.
   - Record the DJM trim/fader/master marks and the meter readings in `measurements/<session>/`.
3. **Noise floor:** everything on, no signal, DJM master at the operating mark. REW noise-floor capture at the centre spot, plus RTA about 1 m from each 812, the KS212C and the center. Hum shows as peaks at 60/120/180 Hz (ground loop); broadband hiss that drops when the DJM master goes to zero is the mixer, and if it stays, it's the DriveRack or the speakers.
4. Timing reference works (and whether the center's double reference is a problem), then one sweep at the centre spot with everything on.

**Session 1 - baseline (mutes only):** each group alone + all, at every spot. Save REW `.mdat` + exports to `measurements/2026-xx-xx-baseline/`. RT60 from the all-on runs.

**Analysis (no changes):** group levels, KS212C vs F1-sub delay and polarity (alignment tool, around the overlap band), response vs a club target (see `asr-nightclub-thread.md`), what AutoEQ1's boosts are actually doing. Output: a written proposal with exact values.

**Session 2+ - changes, one at a time, Tony's OK for each, re-measure after each:**
1. KS212C low-pass on DriveRack (if chosen) + subsonic HP
2. KS212C delay and polarity vs F1 subs
3. Group levels
4. Replace AutoEQ1 boosts with measured cuts (PEQOut1 - there is no PEQOut2, so it probably serves both mains as a stereo pair; verify)
5. Target curve shaping
6. Center fill delay/level
7. Mono vs stereo A/B by ear

Tony saves a new preset (#38) when happy; backup after.

## Tooling to write (after the plan is agreed)
- `rew_measure.py`: preflight (REW version, devices, **input = UMIK-2 with cal path `cal/8111561_90deg.txt` and dBFS@94 dB SPL = -16.25** - REW silently drops to "Default Device" and clears the cal if the mic disconnects, seen 2026-09-29; sample rate, timing ref; DriveRack preset loaded and not modified), mute matrix over UDP with read-back, trigger sweep, name measurement `<group>-<spot>`, restore on exit. `--dry-run` prints everything without setting.
- `rew_to_driverack.py`: turn REW filters into proposed DriveRack PEQ values, printed for review, never applied automatically.

## Open items
- [x] Sub is a QSC KS212C - crossover options from the manual (80/100 Hz, no bypass)
- [ ] DJM-250MK2 visible to the Mac (driver?) - check in Session 0
- [x] Center is a JBL EON610
- [ ] Tony: KS212C display - confirm crossover 80 Hz and delay 0 ms
- [ ] Tony: EON610 onboard EQ flat
- [x] Left stack as the timing clock - yes
- [x] Number of spots - as many as needed (core spots + grid, above)
- [ ] Room sketch with dimensions, speaker positions and grid
- [x] Mic on the BlueRigger 10 m repeater; laptop stays at the booth
- [ ] Center timing method (see Timing section)
- [ ] Max SPL for the loud pass
- [x] Cal file moved into the repo (`cal/`) and REW repointed
