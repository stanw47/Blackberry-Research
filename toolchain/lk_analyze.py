#!/usr/bin/env python3
"""
Analyze the BlackBerry KEYone LK bootloader (emmc_appsboot.mbn).

The file is a Qualcomm MBN-wrapped ELF32 ARM image:
  - ph1 loads at paddr 0x8f600000 from file offset 0x8000
Goal: locate the "Device is unlocked! Skipping verification..." decision and the
LK image_verify / boot_linux_from_mmc signature-bypass surface (CVE-2013-2598,
CVE-2014-0973 family).

Usage:
    py -3.11 lk_analyze.py <emmc_appsboot.mbn> [search-string]
"""
import struct
import sys

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB

LOAD_OFF = 0x8000
LOAD_VADDR = 0x8F600000


def read(path):
    with open(path, "rb") as f:
        return f.read()


def find_string(data, needle):
    """Return list of (file_off, str) for ASCII matches."""
    hits = []
    i = 0
    n = len(data)
    b = needle.encode()
    while True:
        j = data.find(b, i)
        if j < 0:
            break
        # extract full string
        end = j
        while end < n and 32 <= data[end] < 127:
            end += 1
        start = j
        while start > 0 and 32 <= data[start - 1] < 127:
            start -= 1
        hits.append((start, data[start:end].decode("ascii", "replace")))
        i = end
    return hits


def string_refs(data, target_off, code_off, code_size):
    """
    ARM literal pools load a 32-bit constant via LDR Rn, [PC, #imm] or from a pool.
    Find 32-bit words equal to the VA of a target string, then map to the pool.
    """
    va = LOAD_VADDR + (target_off - LOAD_OFF)
    refs = []
    # scan for the VA as a little-endian dword in the code region
    needle = struct.pack("<I", va)
    i = code_off
    end = code_off + code_size
    while True:
        j = data.find(needle, i, end)
        if j < 0:
            break
        refs.append(j)
        i = j + 4
    return va, refs


def disasm(data, off, size, thumb=False):
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB if thumb else CS_MODE_ARM)
    md.detail = True
    start = data[off:off + size]
    va = LOAD_VADDR + (off - LOAD_OFF)
    for insn in md.disasm(start, va):
        yield insn


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    needle = sys.argv[2] if len(sys.argv) > 2 else "Device is unlocked"
    data = read(path)
    total = len(data)
    print(f"[*] file={path}")
    print(f"[*] size={total} bytes, code @ file 0x{LOAD_OFF:x} -> VA 0x{LOAD_VADDR:x}")

    hits = find_string(data, needle)
    print(f"\n[*] string matches for {needle!r}: {len(hits)}")
    for off, s in hits[:10]:
        va = LOAD_VADDR + (off - LOAD_OFF) if off >= LOAD_OFF else 0
        print(f"    file=0x{off:06x} va=0x{va:08x}  {s!r}")
        va, refs = string_refs(data, off, LOAD_OFF, total - LOAD_OFF)
        print(f"      literal (VA 0x{va:08x}) referenced from {len(refs)} site(s):")
        for r in refs[:12]:
            rva = LOAD_VADDR + (r - LOAD_OFF)
            print(f"        pool@ file=0x{r:06x} va=0x{rva:08x}")

    # Also report the key security function symbols' string offsets
    print("\n[*] security-relevant strings:")
    for sym in ("boot_linux_from_mmc", "boot_linux_from_flash", "image_verify",
                "get_unlock_ability", "oem unlock", "verify_hlos_image", "fuse_verify"):
        h = find_string(data, sym)
        for off, s in h[:3]:
            print(f"    0x{off:06x}  {s!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
