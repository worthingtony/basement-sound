# Measurement and tuning plan (DRAFT - not agreed yet)

Status 2026-09-29: plan only. Nothing here has been run. Every DriveRack `set` (including mutes) needs Tony's OK per session.

## What's verified so far
- REW **5.40 Beta 120, API 0.9.4**, running on `localhost:4735`. API has what we need: `measure` (sweeps, acoustic timing reference), `alignment-tool` (sub delay/polarity), `eq` (house curve, match target), `measurements/{id}/rt60`, `spl-meter`, `generator`.
- REW input: **UMIK-2**, cal file `cal/8111561_90deg.txt` (the 90° file - correct for mic pointing up; serial 8111561). REW points at the repo copy ("Input cal processed", 2026-09-29).
- REW sample rate is **44.1 kHz** - change to 48 kHz.
- REW timing reference is **None** - change to Acoustic.
- REW output is "Default Device". **The DJM-250MK2 is not visible to the Mac right now** (not in REW's list or System Information). Unknown whether it's just unplugged or needs Pioneer's driver.
- REW has no dbx EQ profile; use "Generic" / "Configurable PEQ" and translate filters to DriveRack PEQ bands by hand (script).

## Signal path
Mac -> USB -> DJM-250MK2 (one channel, input set to USB) -> master out -> DriveRack In A/B -> outputs 1-4.

DJM must be a fixed, known, flat stage for every measurement:
- Channel EQ at 0 (centre detents), Sound Color FX off, crossfader not cutting that channel, channel fader and master at marked positions, trim noted.
- Photo of the mixer settings goes in `measurements/<session>/`.

## The crossover question: DriveRack or KSub?
Recommendation: **DriveRack** - agreeing with Tony - with one condition.
- Why: one place for the whole sub decision (frequency, slope, delay, polarity), saved in the preset, readable and scriptable, and its phase is known so the alignment math is honest. The KSub's internal filter is a fixed, unknown slope.
- Condition: **only one low-pass in the path.** If the KSub's own crossover can be switched to bypass/thru, do that and set `Sub_LPFrequency` on the DriveRack. If it can't, leave the DriveRack low-pass Out (as now) - stacking two filters just makes an unknown steeper one.
- Needed from Tony: what the KSub's rear panel crossover options are (and exact model).
- Bigger picture: the F1 subs get full range and split to the 812s with their own fixed internal crossover, so the KSub isn't really "crossing to tops" - it **overlaps** the F1 subs. The real choice is:
  - (a) KSub and F1 subs share the same bass band (more headroom; needs delay + polarity alignment - current setup), or
  - (b) KSub low-passed lower (e.g. ~60 Hz) to reinforce only the deepest band.
  Measurement decides. Roadmap item 6 (separate outputs for tops/F1 subs/KSub) would let the DriveRack own every crossover - worth revisiting after this.
- Also consider a subsonic high-pass (~25-30 Hz) on the sub output to save excursion - check what the KSub already does internally first.

## Timing without loopback
USB mic = no loopback, and the DJM and UMIK-2 run on different clocks. Use REW's **acoustic timing reference**:
- Ref played on **L**, measurement sweep on **R**. Left stack (output 1) stays on as the "clock" for every measurement.
- Group under test is fed from R; DriveRack mutes the rest:

| Measure | Out 1 (L stack) | Out 2 (R stack) | Out 3 (KSub) | Out 4 (Center) |
|---|---|---|---|---|
| R stack | on (ref only) | **on** | mute | mute |
| KSub | on (ref only) | mute | **on** | mute |
| Center | on (ref only) | mute | mute | **on** |
| All | on | on | on | on |

- KSub gets L+R, so it also receives the ref, but the ref is high-frequency and its low-pass rejects it.
- **Wrinkle to test in the dry run:** the center also gets L+R, so it plays the ref too - a second ref arrival could confuse REW. If it does, measure the center with a different scheme.
- Left stack alone: mirror image (ref on R, right stack as clock) - or check whether REW allows ref and sweep on the same channel.

## Mic positions
- Mic at standing head height (~1.6-1.7 m), pointing straight up, 90° cal file.
- 5 taped spots on the dance floor (centre + 4 around it) + DJ booth. Same spots every session.
- Needs: long USB cable for the UMIK-2 or the laptop moving with the mic.

## Levels and safety
- Capture noise floor first.
- Sweeps start low; working level ~85 dB C at the centre spot. One short pass at party level (tuning depends on level - see ASR notes). Hearing protection for that pass.
- REW generator protection on; subs watched for over-excursion.
- All mutes go through a script that reads back every set and **restores on exit, including Ctrl-C** (fallback: reload preset #37).

## Sessions
**Session 0 - dry run (no mutes, no DriveRack changes):** DJM visible to Mac, REW at 48 kHz, output = DJM, timing ref works, one sweep at the centre spot with everything on.

**Session 1 - baseline (mutes only):** each group alone + all, at every spot. Save REW `.mdat` + exports to `measurements/2026-xx-xx-baseline/`. RT60 from the all-on runs.

**Analysis (no changes):** group levels, KSub vs F1-sub delay and polarity (alignment tool, around the overlap band), response vs a club target (see `asr-nightclub-thread.md`), what AutoEQ1's boosts are actually doing. Output: a written proposal with exact values.

**Session 2+ - changes, one at a time, Tony's OK for each, re-measure after each:**
1. KSub low-pass on DriveRack (if chosen) + subsonic HP
2. KSub delay and polarity vs F1 subs
3. Group levels
4. Replace AutoEQ1 boosts with measured cuts (PEQOut1 - there is no PEQOut2, so it probably serves both mains as a stereo pair; verify)
5. Target curve shaping
6. Center fill delay/level
7. Mono vs stereo A/B by ear

Tony saves a new preset (#38) when happy; backup after.

## Tooling to write (after the plan is agreed)
- `rew_measure.py`: preflight (REW version, devices, cal file, sample rate, timing ref; DriveRack preset loaded and not modified), mute matrix over UDP with read-back, trigger sweep, name measurement `<group>-<spot>`, restore on exit. `--dry-run` prints everything without setting.
- `rew_to_driverack.py`: turn REW filters into proposed DriveRack PEQ values, printed for review, never applied automatically.

## Open items
- [ ] KSub model and its crossover options
- [ ] DJM-250MK2 visible to the Mac (driver?)
- [ ] Center speaker model
- [ ] OK with left stack as the timing clock?
- [ ] Number of spots, max SPL for the loud pass
- [x] Cal file moved into the repo (`cal/`) and REW repointed
