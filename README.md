# Basement Nightclub - sound system tuning

Tuning Tony's basement DJ system (separate from the upstairs home theater). The goal: sound as good as the best club in the world.

## The system

A **dbx DriveRack VENU360** feeds:

| Output | Speaker |
|---|---|
| Left / Right mains | Bose F1 Subwoofers, each feeding a Bose F1 Model 812 top |
| Mono sub | QSC KS212C (cardioid dual 12") |
| Center fill | JBL EON610 |

Measurement kit: a miniDSP UMIK-2 with REW.

## Where it stands

- Running preset **#37** - the original (#36) plus two changes chosen by ear: the QSC's crossover opened up, and its polarity inverted. Big improvement.
- **Next:** measure with REW (each speaker group alone, then together), then tune - timing, levels, and replacing the auto-EQ boosts with measured cuts. Plan: [`notes/measurement-plan.md`](notes/measurement-plan.md). Waiting on a replacement microphone.

## What's here

| Path | What it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | The full record: wiring, current settings, roadmap, and the DriveRack's control protocol |
| `venu360_backup.py` | Read-only full dump of the DriveRack's settings to `backups/` (`--diff` compares) |
| `venu360_xover_ab.py` | Switches the QSC crossover and polarity for A/B listening, reading back every change |
| `backups/` | Saved states of presets #36 and #37 |
| `notes/` | The measurement plan, and takeaways from a forum thread on nightclub sound |
| `cal/` | The microphone's calibration file (REW reads it from here - don't move it) |

## Rules

- **No changes to the DriveRack without Tony's OK.** Reading is always fine.
- Back up before a session of changes, change one thing at a time, and read back every setting so it can be judged by ear.
