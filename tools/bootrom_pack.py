#!/usr/bin/env python3
"""bootrom_pack.py - build a candidate "bootrom binary" payload for cap.exe,
wrapping boot0.img content so that cap.exe's parser (FUN_00432460 -> 0x432060
+ gate 0x45b880) recognizes the file as such and (hopefully) commits the
regions to the hardware boot0 via the official SWITCH_BOOT lane.

Decoded cap.exe contract (see sniff_bootrom.py):
  +0x00  version (HMIT)            -> tier: <0x30201 need 0xB0,
                                         0x30201..0x303ff need 0xB8,
                                         >=0x30400 need 0xF8
  +0x04  0x54494d48 'HMIT'
  +0x34  (or +0x20) 0xd7b02d1f     bootrom magic
  +0x38  start block, +0x3c end block  (range = end-start)
  table at data + 2*range:
     [table]      >= 0x4000d
     [table+0xa4]  extent > 0
     [table+0x84]  flags bit0
     [table+0x90] / [table+0x98]  counts

The exact layout of the region descriptors inside the table is still being
fixed (0x4522b0 / 0x440d50 / 0x440de0 / 0x440f50). Two presets emit the two
coherent readings; run the classification on Windows and iterate on what
cap.exe prints.
"""
import argparse, os, struct, sys

MAGIC_BOOTROM = 0xD7B02D1F
MAGIC_HMIT = 0x54494D48


def pad(d, n):  # pad or truncate to exactly n bytes
    return (d[:n] + b"\x00" * n)[:n]


def p32(n):
    return struct.pack("<I", n & 0xFFFFFFFF)


def preset_blocks512(image, size_pad=0x20000):
    """Content treated as a block stream; range = whole-file size / 512.

    table lands inside the data (2*range bytes in), which is where the
    parser expects it; fields are aligned on the table struct.
    """
    hdr = bytearray(0x40)
    struct.pack_into("<I", hdr, 0x00, 0x30201)
    struct.pack_into("<I", hdr, 0x04, MAGIC_HMIT)
    struct.pack_into("<I", hdr, 0x20, MAGIC_BOOTROM)
    struct.pack_into("<I", hdr, 0x34, MAGIC_BOOTROM)
    total = 0x40 + ((len(image) + size_pad) & ~(512 - 1))
    rng = total // 512
    struct.pack_into("<I", hdr, 0x38, 0)
    struct.pack_into("<I", hdr, 0x3C, rng)
    out = bytearray(total)
    out[0:0x40] = hdr
    out[0x40:0x40 + len(image)] = image
    tbl = 2 * rng
    struct.pack_into("<I", out, tbl, 0x0004000D)
    out[tbl + 0x84] = 1                      # flags bit0
    struct.pack_into("<I", out, tbl + 0x90, 1)   # regions count
    struct.pack_into("<I", out, tbl + 0x98, len(image) // 512)
    struct.pack_into("<I", out, tbl + 0xA4, 2 * rng)  # extent >= range
    return bytes(out), {"marker": 0x34, "range": rng, "table": tbl}


def preset_regiontable(image, table=0x200):
    """File = small HMIT head + content + table at EOF.

    range kept small (drives the byte-swap region), content extent carried
    by [table+0xa4].  Table placed so all its fields (up to +0xa4+4) fit.
    """
    hdr = bytearray(0x40)
    struct.pack_into("<I", hdr, 0x00, 0x30201)
    struct.pack_into("<I", hdr, 0x04, MAGIC_HMIT)
    struct.pack_into("<I", hdr, 0x20, MAGIC_BOOTROM)
    struct.pack_into("<I", hdr, 0x34, MAGIC_BOOTROM)
    rng = image_len_to_range = (table + len(image) + 0x40) // 2
    struct.pack_into("<I", hdr, 0x38, 0)
    struct.pack_into("<I", hdr, 0x3C, rng)
    tbl = 2 * rng
    while tbl + 0xA8 < 0x40 + table + len(image):
        rng += 1
        tbl = 2 * rng
    struct.pack_into("<I", hdr, 0x3C, rng)
    out = bytearray(tbl + table)
    out[0:0x40] = hdr
    out[0x40:0x40 + len(image)] = image
    struct.pack_into("<I", out, tbl, 0x0004000D)
    out[tbl + 0x84] = 1
    struct.pack_into("<I", out, tbl + 0x90, 1)
    struct.pack_into("<I", out, tbl + 0x98, len(image) // 512)
    struct.pack_into("<I", out, tbl + 0xA4, 2 * rng)
    return bytes(out), {"marker": 0x34, "range": rng, "table": tbl}


PRESETS = {"blocks512": preset_blocks512, "regiontable": preset_regiontable}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="boot0.img content to embed")
    ap.add_argument("-o", "--out", default="bootrom.bin", help="output file")
    ap.add_argument("-p", "--preset", choices=sorted(PRESETS), default="blocks512")
    o = ap.parse_args()
    img = open(o.image, "rb").read()
    blob, meta = PRESETS[o.preset](img)
    open(o.out, "wb").write(blob)
    print("wrote %s (%d bytes) preset=%s %s" % (o.out, len(blob), o.preset, meta))


if __name__ == "__main__":
    main()