#!/usr/bin/env python3
"""
Read-only full backup of the DriveRack VENU360 (all SV parameters) to backups/.

  python3 venu360_backup.py            # writes backups/venu360_full_backup_<local time>.json
  python3 venu360_backup.py --diff FILE  # also compare current unit against an earlier backup

Replies are matched to requests by the echoed path and read until "endls", because
large blocks (AutoEQ curves) arrive in several datagrams and can arrive late.
Only sends 'ls' commands - never changes anything.
"""
import json, os, re, socket, sys, time

UNIT = ("172.16.0.230", 19272)
HERE = os.path.dirname(os.path.abspath(__file__))
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def ls(path, tries=2):
    for _ in range(tries):
        sock.settimeout(0.05)
        try:
            while True: sock.recvfrom(65535)          # drain stale replies
        except socket.timeout: pass
        sock.sendto(f'ls "{path}"\n'.encode(), UNIT)
        buf, end = "", time.time() + 6
        sock.settimeout(3.0)
        while time.time() < end:
            try: data, _ = sock.recvfrom(65535)
            except socket.timeout: break
            buf += data.decode(errors="replace")
            if "endls" in buf: break
        m = re.match(r'ls "(.*?)"', buf)
        if m and m.group(1) == path and "endls" in buf:
            return [(k, v) for k, v in re.findall(r'^\t(\S+) : ?(.*)$', buf, re.M) if k not in ("..", "*")]
    return None

def dump():
    params, skipped = {}, []
    nodes = [n for n, _ in ls(r"\\Node") if n not in ("SV", "AT", "DA")]
    blocks = [n for n, _ in ls(r"\\Preset") if not re.search(r"Meter|^RTA$|^SV$|^AT$|^DA$", n)]
    paths = [r"\\Node\SV"] + [rf"\\Node\{n}\SV" for n in nodes] + \
            [rf"\\Preset\{b}\SV" for b in blocks] + [r"\\Preset\SV"]
    for p in paths:
        r = ls(p)
        if r is None: skipped.append(p); continue
        for k, v in r: params[p + "\\" + k] = v
    return params, skipped

if __name__ == "__main__":
    params, skipped = dump()
    os.makedirs(os.path.join(HERE, "backups"), exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M")
    fn = os.path.join(HERE, "backups", f"venu360_full_backup_{stamp}.json")
    json.dump({"device": UNIT[0], "taken_local": stamp, "skipped_no_reply": skipped,
               "params": params}, open(fn, "w"), indent=1)
    print(f"Saved {fn} ({len(params)} params; skipped: {skipped or 'none'})")
    if "--diff" in sys.argv:
        old = json.load(open(sys.argv[sys.argv.index("--diff") + 1]))["params"]
        live = re.compile(r"Meter|GainReduction|MaxInputLevel")
        diffs = [(k, old.get(k), params.get(k)) for k in sorted(set(old) | set(params))
                 if old.get(k) != params.get(k) and not live.search(k)]
        print(f"{len(diffs)} differences vs {os.path.basename(sys.argv[sys.argv.index('--diff') + 1])}:")
        for k, a, b in diffs: print(f"  {k}: {str(a)[:40]!r} -> {str(b)[:40]!r}")
