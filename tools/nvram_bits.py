#!/usr/bin/env python3
"""
nvram_bits.py - inspect / patch the NV OSSTORE BitFlags record.

RIM updater unlock (oleksandr): "set bits 42 and 43 in block 0x2019 of the
NVRAM". The reference nvram_wp routine reads 0x80 bytes from /dev/nvram at
byte offset 0x2019 (NV_OSSTORE_BitFlags_NUM record).

Run ON the rooted Classic over the serial/ssh shell, NOT on a desktop.

WARNING: only 'inspect' is safe. 'set' and 'clear' modify the NVRAM record.
Back up the 0x80-byte record first (mode 'backup').
"""
import sys, os, struct

DEV = '/dev/nvram'
BIG_BLOCK = 0x2019          # byte offset of the BitFlags record (per rim code)
RECLEN = 0x80

def open_dev():
    for p in (DEV,):
        if os.path.exists(p):
            return os.open(p, os.O_RDWR)
    # fall back to locating nvram partition
    for p in ('/dev/nvram0',):
        if os.path.exists(p):
            return os.open(p, os.O_RDWR)
    sys.exit("no nvram device found on this box")


def read_rec(fd):
    buf = os.pread(fd, RECLEN, BIG_BLOCK)
    if len(buf) != RECLEN:
        sys.exit("pread at 0x%X returned %d bytes (expected %d)" % (BIG_BLOCK, len(buf), RECLEN))
    return bytearray(buf)


def hexdump(buf, base=BIG_BLOCK):
    lines = []
    for i in range(0, len(buf), 16):
        row = buf[i:i + 16]
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        lines.append("  %08X: %s  %s" % (base + i, row.hex(' '), asc))
    return '\n'.join(lines)


def bits42_43():
    """Return (offset_in_record, mask) for LSB-first bit 42/43 -> byte5 bits2+3."""
    off = 42 // 8
    mask = (1 << (42 % 8)) | (1 << (43 % 8))
    return off, mask


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: nvram_bits.py {inspect|set|clear|backup} [file]")
    cmd = sys.argv[1]
    fd = open_dev()
    rec = read_rec(fd)

    if cmd == 'inspect':
        print("record @ 0x%X len 0x%X:" % (BIG_BLOCK, RECLEN))
        print(hexdump(rec))
        off, mask = bits42_43()
        cur = rec[off] & mask
        print("bits 42/43 (buf[%d]&0x%02X) currently = 0x%02X %s"
              % (off, mask, cur, "SET" if cur == mask else ("PARTIAL" if cur else "clear")))
        print("full 128-byte hex to copy blindly:  %s" % rec.hex())
        return 0

    if cmd == 'backup':
        if len(sys.argv) < 3:
            sys.exit("backup needs an output file path")
        open(sys.argv[2], 'wb').write(bytes(rec))
        print("backed up to %s" % sys.argv[2])
        return 0

    if cmd in ('set', 'clear'):
        off, mask = bits42_43()
        print("BEFORE:")
        print(hexdump(rec))
        print("bits 42/43 mapping: buf[0x%02X] mask 0x%02X" % (off, mask))
        before = rec[off] & mask
        if cmd == 'set':
            rec[off] |= mask
        else:
            rec[off] &= ~mask
        after = rec[off] & mask
        os.pwrite(fd, bytes(rec), BIG_BLOCK)
        os.fsync(fd)
        print("%s ok: buf[0x%02X] = 0x%02X -> 0x%02X (bits=0x%02X -> 0x%02X)"
              % (cmd, off, before & 0xFF, after & 0xFF,
                 rec[off] & mask, rec[off] & mask))
        print("RECORD WRITTEN. Full 128-byte hex written: %s" % rec.hex())
        return 0

    sys.exit("unknown cmd %r" % cmd)


if __name__ == '__main__':
    main()