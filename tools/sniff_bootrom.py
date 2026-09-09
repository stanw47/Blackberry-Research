#!/usr/bin/env python3
"""sniff_bootrom.py - offline reimplementation of cap.exe's bootrom-binary
file detection, extracted from cap.exe disassembly:

  FUN_00432460 -> 0x42a1a0 (opens/reads file) -> 0x432060 (structure parse)
  gate 0x441530 -> 0x45b880 (HMIT version/magic/size tiers)

Checks reproduced here exactly as observed:
  * 0x45b880 : version tier at +0, 'HMIT' (0x54494d48) at +4, min sizes
               (0xb0 tier <0x30201, 0xb8 @0x30201-0x303ff, 0xf8 @>=0x30400)
  * 0x432060 : total size > 0x40
               magic 0xd7b02d1f at +0x34 (primary) or +0x20 (fallback)
               start/end blocks at marker+4 / marker+8
               region table at data + 2*range : [table] >= 0x4000d,
               [table+0xa4] > 0 (extent), byte[table+0x84]&1 (flag),
               dword[table+0x90] / dword[table+0x98] (counts)
               byte-swap (rol 0x10) of the region dword area
"""
import struct, sys

MAGIC_BOOTROM = 0xD7B02D1F
MAGIC_HMIT = 0x54494D48


def check_hmit(d, label="0x45b880"):
    """version tier + 'HMIT' magic + minimum size."""
    if len(d) < 4:
        return False, "%s: too short (%d)" % (label, len(d))
    ver = struct.unpack_from("<I", d, 0)[0]
    if ver < 0x30201:
        need = 0xB0
    elif ver < 0x30400:
        need = 0xB8
    else:
        need = 0xF8
    ok_magic = len(d) >= 8 and struct.unpack_from("<I", d, 4)[0] == MAGIC_HMIT
    ok_size = len(d) >= need
    return (ok_magic and ok_size,
            "%s: ver=0x%X need>=0x%X HMIT=%s size_ok=%s" % (label, ver, need, ok_magic, ok_size))


def check_432060(d):
    """the bootrom structure checks from 0x432060."""
    if len(d) <= 0x40:
        return False, "0x432060: size %d <= 0x40" % len(d)
    m = struct.unpack_from("<I", d, 0x34)[0]
    at = 0x34
    if m != MAGIC_BOOTROM:
        if len(d) >= 0x24 and struct.unpack_from("<I", d, 0x20)[0] == MAGIC_BOOTROM:
            m, at = MAGIC_BOOTROM, 0x20
    if m != MAGIC_BOOTROM:
        return False, "0x432060: no 0xd7b02d1f marker at +0x34/+0x20"
    start = struct.unpack_from("<I", d, at + 4)[0]
    end = struct.unpack_from("<I", d, at + 8)[0]
    rng = end - start
    if len(d) <= rng:
        return False, "0x432060: size %d <= range %d (start=%d end=%d)" % (len(d), rng, start, end)
    tbl = 2 * rng
    if len(d) < tbl + 0xa4 + 4:
        return False, "0x432060: table at 0x%X runs past EOF (size %d)" % (tbl, len(d))
    tv = struct.unpack_from("<I", d, tbl)[0]
    if tv < 0x4000d:
        return False, "0x432060: [table]=0x%X < 0x4000d" % tv
    ext = struct.unpack_from("<I", d, tbl + 0xa4)[0]
    if ext == 0:
        return False, "0x432060: [table+0xa4] extent 0"
    flags = d[tbl + 0x84]
    if (flags & 1) != 1:
        return False, "0x432060: [table+0x84] flags 0x%02X bit0 not set" % flags
    c1 = struct.unpack_from("<I", d, tbl + 0x90)[0]
    c2 = struct.unpack_from("<I", d, tbl + 0x98)[0]
    if c1 == 0 and c2 == 0:
        return False, "0x432060: both counts zero"
    return True, ("0x432060: marker at +0x%02X start=%d end=%d range=%d table=0x%X "
                  "[t]=0x%X ext=0x%X flags=0x%02X c1=%d c2=%d" % (at, start, end, rng, tbl, tv, ext, flags, c1, c2))


def sniff(path):
    d = open(path, "rb").read()
    print("== %s (%d bytes)" % (path, len(d)))
    ok1, why1 = check_hmit(d)
    print("  %-40s -> %s" % (why1, "PASS" if ok1 else "FAIL"))
    ok2, why2 = check_432060(d)
    print("  %-40s -> %s" % (why2, "PASS" if ok2 else "FAIL"))
    return ok1 and ok2


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: sniff_bootrom.py <file> ...")
    bad = 0
    for f in sys.argv[1:]:
        if not sniff(f):
            bad += 1
    sys.exit(1 if bad else 0)