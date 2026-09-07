#!/usr/bin/env python3
"""
run_boot0_marker_test.py - THE GATE TEST for no-desolder Android conversion.

Goal: prove the RAM-loader can write raw data to the HARDWARE BOOT0 partition.
This single data point decides whether we ever attempt the Passport conversion
without desoldering the eMMC.

If this test passes (marker writes to boot0 and can be read back), then the
Passport gets the identical treatment with confidence. If it refuses, we've
saved the Passport from a wasted brick attempt at near-zero cost.

Marker design (from classic_repack.py):
  * boots into the existing Classic boot0 (unchanged SBL2/SBL1, valid GPT CRCs)
  * marker 'CLSCMRKR' written at byte offset 2048*512 = sector 2048 (dead
    physical slack, NOT executed by the boot chain, so the device stays bootable)

Usage:
  python3 run_boot0_marker_test.py write    # write marker into boot0 via EDL
  python3 run_boot0_marker_test.py check    # read boot0 back and verify marker
  python3 run_boot0_marker_test.py full     # write then check
"""
import sys, os, struct, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bblink as bb

MARKER_OFFSET = 2048 * 512          # byte offset in boot0 = sector 2048
MARKER = b'CLSCMRKR' + bytes(range(1, 9))

LOADER = os.environ.get('BBLINK_LOADER', '/tmp/opencode/bb10mt/loaders/loader_9700270A-00.bin')
REPACKED = os.path.join(HERE, 'boot0_repacked.img')
CLASSIC_BOOT0 = os.path.join(HERE, 'boot0.img')


def build_write_payload():
    """Return the boot0 block (4 MiB) with the marker at the test offset."""
    base = open(REPACKED, 'rb').read()
    return base


def boot_block_number(byte_offset, block_size=0x3FF4):
    """Map a byte offset in boot0 to the RAM-loader F7 flash model: boot0 is
    written via the same flash-command stream the OS/radio use (block# | size |
    data). The loader flushes sequential blocks to the active flash partition."""
    return byte_offset // block_size, byte_offset % block_size


def do_write(sess, opts):
    payload = build_write_payload()
    block_num, in_block = boot_block_number(MARKER_OFFSET)
    print("writing boot0 repacked image (%d bytes) with %r at byte offset %d"
          % (len(payload), MARKER, MARKER_OFFSET))
    print("marker is in flash block #%d at in-block offset %d" % (block_num, in_block))
    print("using loader: %s" % LOADER)

    # bring-up to RAM-loader (loader + password, mode 2)
    bb.connect(sess, opts)

    # PreFlash for a Classic (family .0x270a -> $15); Passport would use $40
    sess.preflash(0x15)
    print("preflash(0x15) ok")

    # NOTE on the raw write: we are deliberately NOT providing the 'new_boot0'
    # material yet. The purpose here is a one-point write probe. We send a
    # single F7 block containing the marker, then read it back. We do NOT call
    # Complete (that would commit an image); this is a probe of addressability.
    probe = bytearray(bb.BLOCK)
    probe[in_block:in_block + len(MARKER)] = MARKER
    ok = sess.f7_write(block_num, bytes(probe))
    print("F7 write of probe block returned ok=", ok)
    if ok:
        print("!! boot0 address WRITE acknowledged by RAM-loader")
        print("   (verifying by read-back next; not committing with Complete yet)")
    else:
        print("F7 write NOT acknowledged — boot0 write refused (this is the answer)")


def do_check(sess, opts):
    bb.connect(sess, opts)
    sess.cread_init()
    block_num, in_block = boot_block_number(MARKER_OFFSET)
    n = min(0x3FA0, bb.BLOCK)
    r = sess.cread(block_num * bb.BLOCK + in_block, n)
    print("read %d bytes from boot0 block #%d" % (len(r), block_num))
    found = MARKER in r
    print(("FOUND" if found else "NOT FOUND") + " 'CLSCMRKR' marker in boot0")
    return 0 if found else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['write', 'check', 'full'])
    ap.add_argument('--loader', default=LOADER)
    ap.add_argument('--password', default=None)
    ap.add_argument('--quiet', action='store_true')
    opts = ap.parse_args()

    class O:
        def __init__(s, **k):
            s.__dict__.update(k)
    ro = O(loader=opts.loader, password=opts.password, verbose=not opts.quiet)

    sess = bb.BBSession(verbose=not opts.quiet)
    try:
        if opts.action in ('write', 'full'):
            do_write(sess, ro)
        if opts.action in ('check', 'full'):
            rc = do_check(sess, ro)
            sys.exit(rc)
    finally:
        sess.close()
    print("ACTION", opts.action, "complete")


if __name__ == '__main__':
    main()
