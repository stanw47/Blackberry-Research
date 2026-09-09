#!/usr/bin/env python3
import os, struct, sys

BLOCK = 0x10000
TNAMES = {5: "User", 6: "OS/MBR", 8: "IFS", 9: "RFS", 0x89: "SIG2", 0x18: "OS"}

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

def mfcq_info(f, off):
    f.seek(off)
    assert f.read(4) == b"mfcq", "no mfcq magic"
    cksum, version, nheaders, headersz, datacks, flags = struct.unpack("<6I", f.read(24))
    f.seek(off + 0x20)
    assert f.read(4) == b"mfcq", "no mfcq v2"
    v2_cksum, v2_version, v2_length, nfiles, v2_headersz = struct.unpack("<5I", f.read(20))
    fmt = "  v1 ver=%d nheaders=%d headersz=%#x flags=%#x | v2 ver=%#x nfiles=%d headersz=%#x"
    recs = []
    pos = off + 0x3c
    for i in range(nfiles):
        f.seek(pos)
        m = f.read(4)
        if m != b"pfcq":
            recs.append("  rec%d BAD magic %r at %#x" % (i, m, pos))
            break
        version, length, typ, rrec_off, nrec, hwv_off, hwv_n, sig_off, sig_sz, bs = \
            struct.unpack("<10I", f.read(40))
        f.seek(pos + rrec_off)
        rm, rl, rob, rc = struct.unpack("<4sIII", f.read(16))
        blocks = rc
        recs.append("  rec%d type=0x%02x(%s) runs=%d blocks=%d bytes=%d" % (
            i, typ, TNAMES.get(typ, "?"), nrec, blocks, blocks * BLOCK))
        pos += length
    data_end = off + headersz
    return nfiles, headersz, data_end, fmt % (version, nheaders, headersz, flags,
                                              v2_version, nfiles, v2_headersz), recs

def main(path):
    sz = os.path.getsize(path)
    with open(path, "rb") as f:
        cap_end = pe_end(f)
        f.seek(cap_end)
        sig = f.read(12)
        f.read(80)
        nfiles = struct.unpack("<I", f.read(4))[0]
        f.read(4)
        offs = [struct.unpack("<Q", f.read(8))[0] for _ in range(nfiles)]
    print("%s  size=%d (%#x)" % (path, sz, sz))
    print("  cap_end=%#x sig_ok=%s nfiles=%d offs=%s" % (
        cap_end, sig == b"\x9c\xd5\xc5\x97" * 3, nfiles, ["%#x" % o for o in offs]))
    for i, off in enumerate(offs):
        hdrline = f"  file{i} @ %#x: raw-end b'...'; " % off
        with open(path, "rb") as f:
            f.seek(off)
            head = f.read(4)
            print("  file%d @%#x first4=%r" % (i, off, head))
            if head == b"mfcq":
                n, hsz, dend, fmt, recs = mfcq_info(f, off)
                print("    %s" % fmt)
                for r in recs:
                    print("    %s" % r)
                rec_bytes = 0
                for r in recs:
                    rb = int(r.split("bytes=")[1].split()[0], 10)
                    rec_bytes += rb
                expected = hsz + rec_bytes
                nxt = offs[i + 1] if i + 1 < nfiles else sz
                real = nxt - off
                print("    container bytes(off..next/tail)=%d expected(hdr+streams)=%d delta=%+d %s" % (
                    real, expected, real - expected,
                    "OK" if real == expected else "(extra trailer/tail bytes)"))
            else:
                print("    (non-mfcq payload)")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
        print()