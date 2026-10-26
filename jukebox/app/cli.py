"""
Drive VirtualDJ through the Remote protocol from a terminal.

  python3 -m jukebox.app.cli nowplaying [SECONDS]   # watch both decks
  python3 -m jukebox.app.cli folder PATH            # e.g. 'mylists:/ZZZ CLAUDE test.subfolders'
  python3 -m jukebox.app.cli automix                # the Automix list
  python3 -m jukebox.app.cli add CATALOGUE PATH POS # drop PATH from CATALOGUE into Automix at POS

Advertises itself as "ZZZ CLAUDE jukebox" on port 4250 (already accepted in VirtualDJ on
2026-10-25). Only `add` changes anything.
"""
import sys, time
from .vdjremote import VdjRemote

NAME, PORT = "ZZZ CLAUDE jukebox", 4250

# Through the Remote, get_title answers a yes/no and get_time answers nothing (2026-10-25);
# get_title_before_remix is what the real Remote uses, and song_pos runs 0..1.
DECK_QUERIES = {"loaded": "loaded", "artist": "get_artist", "title": "get_title_before_remix",
                "path": "get_filepath", "audible": "is_audible", "pos": "song_pos", "bpm": "get_bpm"}


def show(songs):
    for i, s in enumerate(songs):
        print(f"  {i}: {s.get('artist')} - {s.get('title')}  [{s.get('path')}]")


def nowplaying(vdj, seconds):
    ids = {(d, k): vdj.watch(f"deck {d} {q}") for d in (1, 2) for k, q in DECK_QUERIES.items()}
    end, last = time.time() + seconds, None
    while time.time() < end:
        state = {d: {k: vdj.values.get(ids[(d, k)]) for k in DECK_QUERIES} for d in (1, 2)}
        live = [d for d in (1, 2) if state[d]["audible"]]
        line = "  |  ".join(
            f"deck {d}{' *' if d in live else ''}: " + (
                f"{state[d]['artist']} - {state[d]['title']} ({(state[d]['pos'] or 0):.0%}, "
                f"{(state[d]['bpm'] or 0):.0f} BPM)" if state[d]["loaded"] else "empty")
            for d in (1, 2))
        if line != last:
            print(time.strftime("%H:%M:%S"), line)
            last = line
        time.sleep(0.5)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    vdj = VdjRemote(NAME, PORT)
    try:
        vdj.wait_connected()
        cmd = argv[0]
        if cmd == "nowplaying":
            nowplaying(vdj, float(argv[1]) if len(argv) > 1 else 15)
        elif cmd == "folder":
            show(vdj.folder(argv[1]))
        elif cmd == "automix":
            show(vdj.automix())
        elif cmd == "add":
            catalogue, path, pos = argv[1], argv[2], int(argv[3])
            song = next((s for s in vdj.folder(catalogue) if s.get("path") == path), None)
            if not song:
                sys.exit(f"{path} is not in {catalogue} - not adding")
            show(vdj.add_to_automix(song, pos))
        else:
            sys.exit(__doc__)
    finally:
        vdj.close()


if __name__ == "__main__":
    main(sys.argv[1:])
