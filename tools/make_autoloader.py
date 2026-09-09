#!/usr/bin/env python3
import os, struct, sys, hashlib, argparse

SIG = b"\x9c\xd5\xc5\x97" * 3
PFCQ = 0x71636670

def pe_end(f):
    f.seek(0x3c); pe = struct.unpack("<I", f.read(4))[0]
    f.seek(pe + 6); n = struct.unpack("<H", f.read(2))[0]
    f.seek(pe + 20); osz = struct.unpack("<H", f.read(2))[0]
    base = pe + 24 + osz
    end = 0
    for i in range(n):
        f.seek(base + i * 40 + 20); so = struct.unpack("<I", f.read(4))[0]
        f.seek(base + i * 40 + 16); sr = struct.unpack("<I", f.read(4))[0]
        if so + sr > end:
            end = so + sr
    return end

def file_type(buf):
    if len(buf) < 16:
        return None
    for i in range(len(buf) - 13):
        if struct.unpack_from("<I", buf, i)[0] == PFCQ:
            t = buf[i + 12]
            return {5: "User", 6: "OS", 8: "IFS", 12: "Radio"}.get(t, "QCFM%d" % t)
    return None

def build_autoloader(capexe, files, out, ver=2):
    sizes = [os.path.getsize(x) for x in files]
    with open(capexe, "rb") as f:
        cap_end = pe_end(f)
        f.seek(cap_end)
        head = f.read(0x84)
    if head[0:12] != SIG:
        pass
    with open(out, "wb") as o:
        with open(capexe, "rb") as f:
            f.seek(0)
            remaining = cap_end
            while remaining:
                chunk = f.read(1 << 20)
                if not chunk:
                    raise IOError("short cap.exe")
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]
                o.write(chunk)
                remaining -= len(chunk)
        o.write(SIG)
        o.write(b"\x00" * 80)
        nfiles = len(files)
        off0 = cap_end + 0x84
        offs = []
        off = off0
        for s in sizes:
            offs.append(off)
            off += s
        o.write(struct.pack("<I", nfiles))
        o.write(b"\x00" * 4)
        for off in offs:
            o.write(struct.pack("<Q", off))
        pad = off0 - o.tell()
        if pad < 0:
            raise IOError("too many files for v2 header")
        o.write(b"\x00" * pad)
        for fn in files:
            with open(fn, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    o.write(chunk)
    return offs

def sha256_file(fn):
    h = hashlib.sha256()
    with open(fn, "rb") as f:
        while True:
            c = f.read(1 << 20)
            if not c:
                break
            h.update(c)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    offs = build_autoloader(a.cap, a.files, a.out)
    with open(a.out, "rb") as f:
        cap_end = pe_end(f)
    print("cap_end=%#x" % cap_end)
    for i, (o, fn) in enumerate(zip(offs, a.files)):
        with open(fn, "rb") as f:
            buf = f.read(64)
        print("  file%d off=%#x size=%d type=%s" % (i, o, os.path.getsize(fn), file_type(buf)))
    print("out=%s size=%d sha256=%s" % (a.out, os.path.getsize(a.out), sha256_file(a.out)))

if __name__ == "__main__":
    main()