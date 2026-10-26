#!/usr/bin/env python3
"""
Pose as a VirtualDJ Remote and add one song to Automix by path - no browser steering.

  python3 jukebox/vdj_remote_probe.py              # list the catalogue and the Automix list only
  python3 jukebox/vdj_remote_probe.py add PATH POS # also drop PATH into the Automix list at POS

The protocol was read off the wire on 2026-10-25 (see README, "Breakthrough"): the Remote
advertises Bonjour _vdjremote8._tcp and listens; VirtualDJ connects to it. Messages are
"8JDV" + uint32 LE total length + uint16 LE type + body. This probe advertises itself with
macOS's dns-sd (built in), so VirtualDJ must have "ZZZ CLAUDE jukebox" on its Remote
accept list - it may ask once.

Writes nothing except, with `add`, one song into the Automix list.
"""
import html, io, socket, struct, subprocess, sys, time, re, zipfile
from xml.sax.saxutils import quoteattr

NAME = "ZZZ CLAUDE jukebox"
PORT = 4250
CATALOGUE = "mylists:/ZZZ CLAUDE test.subfolders"
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
WAIT = int(sys.argv[sys.argv.index("--wait") + 1]) if "--wait" in sys.argv else 90

T_HELLO, T_INFO, T_FOLDER_REQ, T_FOLDER_XML, T_FOLDER_UPDATE, T_BYE = 39, 64, 36, 37, 50, 20


def frame(mtype, body=b""):
    return b"8JDV" + struct.pack("<IH", 10 + len(body), mtype) + body


def read_msgs(sock, buf):
    """Return (messages, leftover). Each message is (type, body after the type)."""
    try:
        data = sock.recv(1 << 16)
    except socket.timeout:
        return [], buf
    if not data:
        raise ConnectionError("VirtualDJ closed the connection")
    buf += data
    msgs = []
    while len(buf) >= 8:
        if buf[:4] != b"8JDV":
            j = buf.find(b"8JDV", 1)
            buf = buf[j:] if j > 0 else b""
            continue
        n = struct.unpack("<I", buf[4:8])[0]
        if len(buf) < n:
            break
        msgs.append((struct.unpack("<H", buf[8:10])[0], buf[10:n]))
        buf = buf[n:]
    return msgs, buf


def folder_xml(body):
    # body: uint16 flag, uint32 encoding (1 = XML, 2 = zip holding data.xml), payload
    if struct.unpack("<I", body[2:6])[0] == 2:
        return zipfile.ZipFile(io.BytesIO(body[6:])).read("data.xml").decode("utf-8", "replace")
    return body[6:].decode("utf-8", "replace")


def files(xml):
    return [{k: html.unescape(v) for k, v in re.findall(r'(\w+)="([^"]*)"', m)}
            for m in re.findall(r"<file (.*?)>", xml)]


def main():
    add = len(sys.argv) > 3 and sys.argv[1] == "add"
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(1)
    srv.settimeout(WAIT)
    adv = subprocess.Popen(["dns-sd", "-R", NAME, "_vdjremote8._tcp", "local.", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Advertising {NAME!r} on :{PORT}; waiting up to {WAIT} s for VirtualDJ to connect")
    try:
        conn, peer = srv.accept()
    except socket.timeout:
        adv.terminate()
        sys.exit("VirtualDJ never connected - is the name on its Remote accept list?")
    print(f"VirtualDJ connected from {peer}")
    conn.settimeout(0.5)
    conn.sendall(frame(T_HELLO, b"\x49\x03"))
    conn.sendall(frame(T_INFO, struct.pack("<HI", 0, 1) +
                       b'<?xml version="1.0" encoding="UTF-8"?>\r\n<info build="9618" skin="Default:4x3T" '
                       b'width="1000" height="1000" dpi="1.0" />\r\n'))
    conn.sendall(frame(T_FOLDER_REQ, struct.pack("<H", 1) + CATALOGUE.encode()))
    conn.sendall(frame(T_FOLDER_REQ, struct.pack("<H", 1) + b"playlist"))

    buf, seen, folders, deadline = b"", {}, {}, time.time() + 10
    while time.time() < deadline and not {CATALOGUE, "playlist"} <= folders.keys():
        msgs, buf = read_msgs(conn, buf)
        for t, body in msgs:
            seen[t] = seen.get(t, 0) + 1
            if t == T_FOLDER_XML:
                x = folder_xml(body)
                p = re.search(r'<foldercontent path="([^"]*)"', x)
                if p:
                    folders[p.group(1)] = x
    print("message types from VirtualDJ:", dict(sorted(seen.items())))
    for path in (CATALOGUE, "playlist"):
        fs = files(folders.get(path, ""))
        print(f"\n{path}: {len(fs)} songs")
        for i, f in enumerate(fs):
            print(f"  {i}: {f.get('artist')} - {f.get('title')}  [{f.get('path')}]")
    if OUT:
        open(OUT, "w").write("\n\n".join(folders.values()))

    if add:
        path, pos = sys.argv[2], int(sys.argv[3])
        song = next((f for f in files(folders.get(CATALOGUE, "")) if f.get("path") == path), None)
        if not song:
            sys.exit(f"{path} is not in the catalogue - not adding")
        attrs = " ".join(f"{k}={quoteattr(song[k])}" for k in ("path", "artist", "title", "remix", "bpm", "key", "length") if k in song)
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\r\n<folderupdate path="playlist" name="playlist">\r\n'
               f'\t<filedrop {attrs} position="{pos}" />\r\n</folderupdate>\r\n')
        conn.sendall(frame(T_FOLDER_UPDATE, struct.pack("<HI", 0, 1) + xml.encode()))
        print(f"\nsent filedrop {song.get('artist')} - {song.get('title')} at position {pos}")
        time.sleep(1.5)
        conn.sendall(frame(T_FOLDER_REQ, struct.pack("<H", 1) + b"playlist"))
        deadline, after = time.time() + 5, None
        while time.time() < deadline and after is None:
            msgs, buf = read_msgs(conn, buf)
            for t, body in msgs:
                if t == T_FOLDER_XML and 'path="playlist"' in folder_xml(body)[:200]:
                    after = files(folder_xml(body))
        print("Automix list after:")
        for i, f in enumerate(after or []):
            print(f"  {i}: {f.get('artist')} - {f.get('title')}  [{f.get('path')}]")

    conn.sendall(frame(T_BYE))
    conn.close()
    adv.terminate()


if __name__ == "__main__":
    main()
