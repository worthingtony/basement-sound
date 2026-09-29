#!/usr/bin/env python3
"""
A/B toggle for the QSC sub crossover (output 3, "Mono Sub") on the DriveRack VENU360.

  python3 venu360_xover_ab.py status   # read-only: show current sub crossover
  python3 venu360_xover_ab.py normal   # QSC polarity normal
  python3 venu360_xover_ab.py invert   # QSC polarity inverted
  python3 venu360_xover_ab.py A        # original: sub high-pass 102 Hz, low-pass Out
  python3 venu360_xover_ab.py B        # proposed: sub high-pass Out, low-pass Out
                                       # (the QSC's own 80 Hz crossover does the low-pass)

Only touches the Sub band of the 2x3 crossover (CrossoverIIR1). Slope types stay
LR 48 in both. In B the DriveRack sends the sub everything and the QSC's own
80 Hz crossover does the low-pass (no stacked filters). Every change is
read back; if B doesn't read back correctly it switches back to A automatically.
Mains, center, delays, EQ and levels are never touched.
"""
import socket, sys

UNIT = ("172.16.0.230", 19272)
BASE = r"\\Preset\CrossoverIIR1\SV"
HP, LP = BASE + r"\Sub_HPFrequency", BASE + r"\Sub_LPFrequency"
POL = BASE + r"\Sub_Polarity"

SETTINGS = {
    "A": [(HP, "102", "102Hz"), (LP, "Out", "Out")],   # original
    "B": [(HP, "Out", "Out"),   (LP, "Out", "Out")],   # proposed: let the QSC's 80 Hz filter work
}
# order matters for B: lift the high-pass first so the pass band never collapses

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def ask(cmd):
    sock.settimeout(0.05)
    try:
        while True: sock.recvfrom(65535)          # drain stale replies
    except socket.timeout: pass
    sock.sendto((cmd + "\n").encode(), UNIT)
    sock.settimeout(2.0)
    try:
        data, _ = sock.recvfrom(65535)
        return data.decode(errors="replace").strip()
    except socket.timeout:
        return ""

def get(path):
    r = ask(f'get "{path}"')
    return r.rsplit('"', 2)[-2] if r.count('"') >= 4 else None

def show():
    vals = {p.rsplit("\\", 1)[1]: get(p) for p in (HP, LP)}
    types = {n: get(BASE + "\\" + n) for n in ("Sub_HPType", "Sub_LPType")}
    hp, lp = vals["Sub_HPFrequency"], vals["Sub_LPFrequency"]
    mode = "A (original)" if (hp, lp) == ("102Hz", "Out") else \
           "B (proposed)" if (hp, lp) == ("Out", "Out") else "custom"
    print(f"Sub high-pass: {hp} ({types['Sub_HPType']})")
    print(f"Sub low-pass : {lp} ({types['Sub_LPType']})")
    print(f"Mode: {mode}")
    print(f"Sub polarity : {get(POL)}")
    return hp, lp

def apply(mode):
    for path, value, expect in SETTINGS[mode]:
        ask(f'set "{path}" {value}')
        got = get(path)
        if got != expect:
            return f"{path.rsplit(chr(92),1)[1]} read back {got!r}, expected {expect!r}"
    return None

if __name__ == "__main__":
    arg = (sys.argv[1] if len(sys.argv) > 1 else "status").upper()
    if arg == "STATUS":
        show()
    elif arg in ("NORMAL", "INVERT"):
        want = "Normal" if arg == "NORMAL" else "Inverted"
        ask(f'set "{POL}" {want}')
        got = get(POL)
        if got != want: print(f"Problem: polarity read back {got!r}, expected {want!r}")
        show()
    elif arg in SETTINGS:
        err = apply(arg)
        if err and arg == "B":
            print("Problem:", err, "- switching back to A")
            err2 = apply("A")
            if err2: print("WARNING: could not restore A:", err2, "- reload preset 36 from the front panel")
        elif err:
            print("Problem:", err, "- reload preset 36 from the front panel if unsure")
        show()
    else:
        print(__doc__)
