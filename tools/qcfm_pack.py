#!/usr/bin/env python3
import os
import struct
import sys
import zlib

BLOCK = 0x10000

TYPES = {
    "ufs": 0x05, "mbr": 0x06, "sig": 0x07, "ifs": 0x08, "rcfs": 0x09,
    "os": 0x18, "sig2": 0x89,
}

def size_to_blocks(n):
    return (n + BLOCK - 1) // BLOCK

def crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF

def pack_mfcq(out, files):
    total = len(files)
    mhf1_len = 0x20
    mhf2_len = 0x1c
    cf2_len = 0x2c
    rrec_len = 0x10

    mhf1_dat = bytearray(mhf1_len)
    struct.pack_into("<4sIIIIII4s", mhf1_dat, 0,
                     b"mfcq", 0, 1, 0, 0, 0, 0, b"\x00" * 4)

    cf2s = []
    rrecs = []
    mhf1dat = 0
    for spec in files:
        fn, _, tstr = spec.partition(",")
        t = int(tstr, 0) if tstr else TYPES.get(os.path.splitext(fn)[1].lstrip("."), 0)
        size = os.path.getsize(fn)
        c = size_to_blocks(size)
        cf2 = bytearray(cf2_len)
        struct.pack_into("<4sIIIIIIIIII", cf2, 0,
                         b"pfcq", 0x20000, cf2_len + rrec_len, t, cf2_len, 1,
                         0, 0, 0, 0, BLOCK)
        rrec = bytearray(rrec_len)
        struct.pack_into("<4sIII", rrec, 0, b"rrcq", rrec_len, 0, c)
        cf2s.append(cf2)
        rrecs.append(rrec)
        mhf1dat += cf2_len + c * rrec_len

    headersz = mhf1_len + mhf2_len + total * (cf2_len + rrec_len)
    mhf2_dat = bytearray(mhf2_len)
    struct.pack_into("<4sIIII", mhf2_dat, 0,
                     b"mfcq", 0, 0x20000, mhf2_len, total)
    struct.pack_into("<I", mhf2_dat, 0x14, headersz)

    struct.pack_into("<I", mhf1_dat, 0x08, 1)
    struct.pack_into("<I", mhf1_dat, 0x10, headersz + 0x20)
    struct.pack_into("<I", mhf1_dat, 0x18, mhf1_len)

    out.write(mhf1_dat)
    out.write(mhf2_dat)
    for cf2, rrec in zip(cf2s, rrecs):
        out.write(cf2)
        out.write(rrec)

    need = headersz + 0x20 - out.tell()
    if need > 0:
        out.write(b"\x00" * need)

    for spec in files:
        fn = spec.partition(",")[0]
        size = os.path.getsize(fn)
        blocks = size_to_blocks(size)
        with open(fn, "rb") as f:
            for b in range(blocks):
                data = f.read(BLOCK)
                if len(data) < BLOCK:
                    data += b"\x00" * (BLOCK - len(data))
                out.write(data)

def main():
    out, files = sys.argv[1], sys.argv[2:]
    if not files:
        sys.exit("usage: qcfm_pack.py out.mfcq file...")
    with open(out, "wb") as f:
        pack_mfcq(f, files)
    print("wrote %s size=%d" % (out, os.path.getsize(out)))

if __name__ == "__main__":
    main()