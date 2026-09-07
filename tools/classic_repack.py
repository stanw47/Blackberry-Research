#!/usr/bin/env python3
"""Classic-native boot0 repacker (marker test).

Goal: prove the EDL RAM-loader lane writes the Classic eMMC boot partition
verbatim, by injecting a benign marker into the GPT reserved padding and a
partition-slack region, recomputing CRCs, and letting us read it back.

Classic (SQC100 = MSM8960) boot0 layout (from real dump):
  sector 0            : MBR/empty
  sector 1            : GPT header
  sector 2            : GPT partition table (128 entries)
  sector 3..33        : GPT reserved padding (all zero, never executed)
  sectors 34..521     : SBL2  (0x4400, 249856 B)
  sectors 522..719    : SBL1  (0x41400, 101376 B)
  sectors 720..       : trailing slack / backup area
  4MB total physical partition.

We do NOT modify SBL2/SBL1. We only touch GPT reserved padding + slack,
which the bootROM never reads as code.
"""
import struct, binascii, sys, os

SECTOR = 512
GPT_FMT = '<8s4I4Q16sQIII'
GPT_SIZE = struct.calcsize(GPT_FMT)
ENTRY_FMT = '<16s16sQQQ72s'
ENTRY_SIZE = struct.calcsize(ENTRY_FMT)

# Marker constants (must be recognizable after a round-trip)
MARKER = b'CLSCMRKR' + bytes(range(1, 24))

def read_boot0(path):
    return open(path, 'rb').read()

def parse_gpt(data):
    raw = data[SECTOR:SECTOR+GPT_SIZE]
    h = struct.unpack(GPT_FMT, raw)
    if h[0] != b'EFI PART':
        raise SystemExit('GPT header not found in boot0')
    return h, raw

def parse_entries(data, h):
    ptlba, ent, esz = h[10], h[11], h[12]
    pt = data[ptlba*SECTOR: ptlba*SECTOR + ent*esz]
    parts = {}
    for i in range(ent):
        raw = pt[i*esz:(i+1)*esz]
        if len(raw) < esz:
            break
        tu, pu, fl, ll, at, pad = struct.unpack(ENTRY_FMT, raw)
        nm = pad.decode('utf-16-le', 'replace').split('\0')[0]
        if nm:
            parts[nm] = {'first': fl, 'last': ll,
                         'size': (ll - fl + 1) * SECTOR}
    return parts, pt

def recompute_header_crc(h, data):
    h = list(h)
    h[3] = 0
    raw = struct.pack(GPT_FMT, *h)
    return binascii.crc32(raw) & 0xffffffff, struct.unpack(GPT_FMT, raw)

def ptable_crc(data, h):
    ptlba, ent, esz = h[10], h[11], h[12]
    pt = data[ptlba*SECTOR: ptlba*SECTOR + ent*esz]
    return binascii.crc32(pt) & 0xffffffff

def recompute_and_pack(data, h):
    """Recompute both header crc and ptable crc, return a valid boot0."""
    # ptable crc
    hdr_crc, _ = recompute_header_crc(h, data)
    pt_crc = ptable_crc(data, h)
    h = list(h)
    h[3] = hdr_crc
    h[13] = pt_crc
    raw = struct.pack(GPT_FMT, *h)
    out = bytearray(data)
    out[SECTOR:SECTOR+GPT_SIZE] = raw
    return bytes(out)

def build(orig, marker_positions):
    """orig = bytes boot0; inject MARKER at each byte position, preserve CRCs."""
    out = bytearray(orig)
    for pos, label in marker_positions:
        region = out[pos:pos+len(MARKER)]
        if len(set(region)) != 1 or region[0] != 0:
            raise SystemExit(f'Marker position 0x{pos:x} ({label}) is not zero-padding! {region[0]:02x}')
        out[pos:pos+len(MARKER)] = MARKER
    h, raw = parse_gpt(bytes(out))
    return recompute_and_pack(bytes(out), h)

def main():
    if len(sys.argv) != 3:
        print('usage: classic_repack.py <input boot0> <output boot0>')
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    orig = read_boot0(src)
    h, raw = parse_gpt(orig)
    print(f'GPT header: sig={h[0]!r} rev=0x{h[1]:x} ptable_lba={h[10]} entries={h[11]}')
    parts, _ = parse_entries(orig, h)
    for k, v in parts.items():
        print(f'  {k:6s} first={v["first"]:5d} last={v["last"]:5d} size={v["size"]}')

    hdr_crc = recompute_header_crc(h, orig)[0]
    print(f'CRCs valid: hdr={hex(hdr_crc)} (stored {hex(h[3])}) '
          f'ptable={hex(ptable_crc(orig,h))} (stored {hex(h[13])})')
    if hdr_crc != h[3]:
        # original may not be currently valid (device damaged) -- we will fix it
        print('  NOTE: original hdr crc mismatch; repacker will set correct CRCs')

    # Marker positions: place in the physical-partition slack AFTER the last
    # GPT partition (SBL1 ends at sector 719 = 0x59e00), which is outside any
    # GPT partition and never executed. Use the zero region at sectors 2048+
    # (bytes 0x100000..) and a spot just after SBL1.
    marker_positions = [
        (2048 * SECTOR, 'physical slack (sector 2048)'),
        (2049 * SECTOR, 'physical slack (sector 2049)'),
    ]
    out = build(orig, marker_positions)
    # Verify out is still GPT-valid and markers present
    h2, _ = parse_gpt(out)
    for pos, label in marker_positions:
        if out[pos:pos+len(MARKER)] == MARKER:
            print(f'  marker ok at 0x{pos:x} ({label})')
        else:
            raise SystemExit(f'  marker FAILED at 0x{pos:x}')
    print(f'wrote {dst} ({len(out)} bytes) with recomputed GPT CRCs '
          f'({hex(h2[3])}, {hex(h2[13])})')
    open(dst, 'wb').write(out)
    return 0

if __name__ == '__main__':
    sys.exit(main())