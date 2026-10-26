#!/usr/bin/env python3
"""
Probe VirtualDJ's Network Control plugin: can a script put a specific song into Automix?

  python3 jukebox/vdj_probe.py read           # read-only: plugin up? decks, Automix list
  python3 jukebox/vdj_probe.py find "term"    # search VirtualDJ's browser, show the top hit
  python3 jukebox/vdj_probe.py add "term"     # find, then add the top hit next in Automix
                                              # and read it back

The whole jukebox design hangs on `add`: the documented verbs only add whatever is
selected in VirtualDJ's browser (automix_add_next), so this checks whether a search
leaves the top hit selected and whether that exact song lands next in Automix.

Setup on the VirtualDJ computer: Config > Extensions > Effects > Other > Network
Control > Install, then Master panel > effect slot > Auto-Start > Network Control,
cog wheel for the port (default 8080) and password. It only listens once enabled.

  VDJ_HOST      VirtualDJ computer (default 127.0.0.1)
  VDJ_PORT      default 8080
  VDJ_PASSWORD  the plugin's password, if set - pass it with secret-run, never inline

Only get_/is_/file_count verbs are queried: through /query an action verb such as
`play` or `automix` might run rather than report. `find` changes the search box;
`add` changes the Automix list (one song, which you can delete by hand). Nothing
else is touched.
"""
import os, sys, time, urllib.error, urllib.parse, urllib.request

HOST = os.environ.get("VDJ_HOST", "127.0.0.1")
PORT = os.environ.get("VDJ_PORT", "8080")
PASSWORD = os.environ.get("VDJ_PASSWORD", "")
BASE = f"http://{HOST}:{PORT}"

def call(endpoint, script):
    url = f"{BASE}/{endpoint}?script={urllib.parse.quote(script)}"
    req = urllib.request.Request(url)
    if PASSWORD:
        req.add_header("Authorization", f"Bearer {PASSWORD}")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.read().decode(errors="replace").strip()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit(f"HTTP {e.code} from {endpoint} '{script}' - wrong or missing password")
        return f"<HTTP {e.code}>"  # e.g. a verb the plugin rejects; report it and carry on
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        sys.exit(f"No answer from {BASE} ({getattr(e, 'reason', e)}). Is Network Control enabled "
                 "in Master Effect > Auto-Start? From another computer it may also be the macOS "
                 "firewall, or the plugin may only listen on the VirtualDJ computer itself.")

def query(script):
    return call("query", script)

def execute(script):
    return call("execute", script)

def song(prefix):
    # prefix is a verb taking a property name, e.g. "get_browsed_song"
    return {p: query(f"{prefix} '{p}'") for p in ("artist", "title")}

def label(s):
    return f"{s['artist']} - {s['title']}"

def automix_state():
    return {"count": query("file_count automix"),
            "position": query("get_automix_position"),
            "next": label(song("get_automix_song")),
            "time_left": query("get_playlist_time")}

def alive():
    clock = query("get_clock")
    if clock.startswith("<HTTP"):
        sys.exit(f"Plugin at {BASE} answered get_clock with {clock} - is that Network Control?")
    return clock

def show_read():
    print(f"Plugin at {BASE}: get_clock = {alive()!r}")
    for d in (1, 2):
        print(f"Deck {d}: {query(f'deck {d} get_artist')!r} - {query(f'deck {d} get_title')!r}"
              f"  is_audible={query(f'deck {d} is_audible')!r}")
    for k, v in automix_state().items():
        print(f"Automix {k}: {v!r}")

def find(term):
    term = term.replace('"', "").replace("'", "")
    script = f'search "{term}"'
    print(f"execute {script} -> {execute(script)!r}")
    time.sleep(1.5)  # VirtualDJ fills search results asynchronously
    hit = song("get_browsed_song")
    print(f"Browser shows {query('file_count')!r} files; selected: {label(hit)!r}")
    print(f"Selected file: {query('get_browsed_filepath')!r}")
    return hit

def add(term):
    alive()
    before = automix_state()
    print(f"Automix before: {before}")
    hit = find(term)
    if not hit["title"]:
        sys.exit("Search left nothing selected - automix_add_next would add nothing. "
                 "Next to try: a one-song playlist via browser_gotofolder.")
    print(f"execute automix_add_next -> {execute('automix_add_next')!r}")
    time.sleep(0.5)
    after = automix_state()
    print(f"Automix after:  {after}")
    landed = after["next"] == label(hit)
    grew = before["count"] != after["count"]
    print(f"Next in Automix is the selected song: {'YES' if landed else 'NO'}; "
          f"list count changed: {'yes' if grew else 'no'}")
    sys.exit(0 if landed else 1)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "read":
        show_read()
    elif cmd == "find" and len(sys.argv) > 2:
        alive()
        find(" ".join(sys.argv[2:]))
    elif cmd == "add" and len(sys.argv) > 2:
        add(" ".join(sys.argv[2:]))
    else:
        sys.exit(__doc__)
