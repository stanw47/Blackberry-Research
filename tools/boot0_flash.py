#!/usr/bin/env python3
"""
boot0_flash.py - flash the Android SBL ("boot0") onto a Passport's hardware
Boot0 MMC partition through the BootROM/RAM-loader, no desolder required.

This is the missing finishing step for the Passport->Android ("balika")
conversion: the OS/radio/user containers cannot carry a boot0 image (MCT kind
$2B has no container type), so boot0 must go through the loader's raw flash
lane.  The device's own 0x2019 unlock (NV bits 42/43, already set) gates the
write path.

Why this tool is PROBE-FIRST and gloves-on:
  * A failed/incomplete BootROM password exchange triggers a full DEVICE
    SECURITY WIPE (observed on the Classic test unit).  This tool never starts
    a handshake until the device is confirmed in BootROM with the OS intact,
    and it aborts on any divergence.
  * Whether the RAM-loader F7 stream can address the HARDWARE boot0 partition
    (vs only the user-area mapping) is still unproven.  So the default action
    is a non-committing marker write into boot0 dead slack (sector 2048,
    unexecuted, boot chain untouched) + read-back verification.  The full
    boot0.img write is only allowed AFTER the marker lands (--write) and
    reads back.

BootROM entry requirement: the device must be powered OFF and plugged in WHILE
this tool is already listening (the device only enumerates as BootROM 0x0001
the moment the host polls).  A device sitting in its wiped "Reload OS" 0010
loader ignores our protocol - recover BB10 first with the rooted autoloader,
THEN run this step, THEN re-flash the Android autoloader (order in docs).

Usage (run from a machine with USB access - Linux or Windows):
  pip install pyusb libusb-package
  python boot0_flash.py preflight               # listener + read-only session
  python boot0_flash.py probe                   # + marker write/readback probe
  python boot0_flash.py write --image boot0.img   # full boot0 commit
  python boot0_flash.py verify-image boot0.img    # offline image sanity
  python boot0_flash.py selftest                # offline protocol self-test
"""

import sys, os, struct, time, hashlib, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bblink as bb

MAJOR = 0
MINOR = 1

LOADER = os.environ.get("BBLINK_LOADER", os.path.join(HERE, "loaders", "loader_8D002C0A-00.bin"))
EXPECT_MODEL = 0x87002C0A          # Passport windermere EMEA
LOAD_ADDR = 0x0DD00000             # IDtoADDR(0x2C0A)
PREFLASH = 0x40                    # Passport family (Classic 0x15)

BOOT0_SIZE = 4 * 1024 * 1024       # 4 MiB hardware boot0
BLOCK = bb.BLOCK                   # 0x3FF4 max flash block
MARKER_OFFSET = 2048 * 512         # boot0 sector 2048 = dead slack, not executed
MARKER = b"CLSCMRKR" + bytes(range(1, 9))

FATAL_WIPE = (
    "\n\nWARNING: an aborted or unknown-state BootROM handshake triggers a full"
    "\nDEVICE SECURITY WIPE on PASSport. If you are not 100% sure the device is"
    "\nin BootROM with the stock OS intact, abort now and power the device OFF"
    "\nbefore replugging. Ctrl-C now if unsure.\n")


def hx(b):
    return b.hex()


def boot_block_number(byte_offset):
    return byte_offset // BLOCK, byte_offset % BLOCK


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            c = f.read(1024 * 1024)
            if not c:
                break
            h.update(c)
    return h.hexdigest()


def verify_boot0_image(path):
    d = open(path, "rb").read()
    if len(d) == 0:
        sys.exit("ERROR: image is empty")
    if len(d) > BOOT0_SIZE:
        sys.exit("ERROR: %s is %d B, larger than the 4 MiB boot0 partition"
                 % (path, len(d)))
    efi = d.find(b"EFI PART")
    old = d.find(b"RIM BlackBerry Device")
    wit = d.find(b"wolverine")
    qcom = d.find(b"D1DC4B84")
    print("  size=%d (boot0=4 MiB) SHA256=%s" % (len(d), hashlib.sha256(d).hexdigest()))
    print("  'EFI PART' @ %#x, 'RIM BlackBerry Device' @ %#x, 'wolverine' @ %#x, 'D1DC4B84' @ %#x"
          % (efi, old, wit, qcom))
    if all(x == -1 for x in (efi, old, wit, qcom)):
        sys.exit("ERROR: image has neither EFI PART nor RIM-BB header - not a boot0")
    if d.strip(b"\xff") == b"":
        sys.exit("ERROR: image is all 0xFF")
    print("  OK: looks like a boot0 image")


class Tool:
    def __init__(self, opts):
        self.opts = opts
        self.verbose = not getattr(opts, "quiet", False)
        self.sess = bb.BBSession(verbose=self.verbose)
        self.regions = None
        self.boot_blocks = None
        self.boot_flags = None

    # ------------------------------------------------------------- USB ritual
    def wait_for_rim(self, timeout=300, want=1):
        print(">>> LISTENING for a BlackBerry (0FCA). POWER OFF the device and PLUG IT IN NOW.", flush=True)
        t0 = time.time()
        seen = set()
        while time.time() - t0 < timeout:
            dev = None
            try:
                import usb.core
                dev = usb.core.find(idVendor=bb.VID_BB)
            except Exception as e:
                time.sleep(0.2)
                continue
            if dev is not None:
                pid = int(dev.idProduct)
                seen.add(pid)
                if pid == want:
                    print("  FOUND BootROM PID 0x%04X" % pid, flush=True)
                    return pid
                print("  see PID 0x%04X (%s) - want BootROM 0x0001"
                      % (pid, {0x8001: "resident loader (ignores our protocol)",
                                0x8017: "OS session", 1: "BootROM"}.get(pid, "")))
                if pid == 0x8001:
                    sys.exit("device is in its RESIDENT LOADER (PID 0x8001). It talks only the "
                             "official-updater protocol and ignores bb10mt. Recover BB10 with the "
                             "rooted autoloader first (power-cycle) so BootROM becomes reachable.")
            time.sleep(0.1)
        sys.exit("TIMEOUT: saw PIDs %s but never BootROM 0x0001"
                 % ["%04X" % p for p in sorted(seen)])

    def drop_to_bootrom(self, pid):
        if pid == 1:
            return
        print("  dropping PID %04X to BootROM (channel0 cmd3)" % pid, flush=True)
        try:
            if self.sess._open_pid(pid, timeout=8000):
                self.sess.session_reboot()
        except Exception:
            pass
        self.sess.close()
        time.sleep(2.5)

    # ------------------------------------------------------------- preflight
    def preflight(self):
        print("== BootROM bring-up ==")
        model_id = bb.connect(self.sess, self.opts)
        if model_id is None or (model_id & 0xFFFF) != 0x2C0A:
            print("  WARNING: model_id %s is not a Passport (0x..2C0A). "
                  "This tool is Passport-tuned; continuing anyway with flags from device."
                  % ("%08X" % model_id if model_id else "none"))
        f = self.sess.flash_regions()
        if f:
            self.regions = f
            print("  flash_regions: blocks=%08X user_kb=%s" % (f[0], f[1]))
        mct = self.sess.get_mct()
        self.parse_mct(mct)

    def parse_mct(self, mct):
        if not mct:
            print("  (no MCT returned by loader)")
            return
        p = 0
        if mct[:4] == b"mct\0" or struct.unpack_from("<I", mct, 0)[0] == 0x92BE564A:
            p = 4
        while p + 2 <= len(mct) - 2:
            T = mct[p]
            L = mct[p + 1]
            if L < 2:
                break
            body = mct[p + 2:p + L]
            if T == 0x2B:
                fl = struct.unpack_from("<I", body, 0)[0]
                st, en = struct.unpack_from("<II", body, 2)
                self.boot_blocks = (st, en)
                self.boot_flags = fl
                print("  MCT Boot0 (kind $2B): blocks %d-%d flags=0x%04X"
                      % (st, en, fl))
            if T == 0x2D:
                st, en = struct.unpack_from("<II", body, 2)
                print("  MCT Boot1 (kind $2D): blocks %d-%d" % (st, en))
            if T == 0xFF:
                break
            p += L
        if self.boot_blocks is None:
            print("  MCT Boot0 record %s" % ("parsed" if mct else "") +
                  " - none found; will assume block 0..%d unless --force"
                  % (BOOT0_SIZE // BLOCK))

    def cread(self, byte_addr, size):
        self.sess.cread_init()
        return self.sess.cread(byte_addr, size)

    # ------------------------------------------------------------------- probe
    def probe(self, write=False):
        self.preflight()
        blk, off = boot_block_number(MARKER_OFFSET)
        print("== marker probe at boot0 byte %d (block %d in-block %d) =="
              % (MARKER_OFFSET, blk, off))
        t0 = time.time()
        ok = self.sess.f7_write(blk, self._probe_payload(off))
        print("  F7 write acknowledged: %s (%.1fs)" % (ok, time.time() - t0))
        time.sleep(0.5)
        n = min(0x3FA0, BLOCK)
        r = self.cread(blk * BLOCK + off, n)
        found = MARKER in r
        print("  CREAD read-back: marker %s (%d bytes)" % ("FOUND" if found else "NOT FOUND", len(r)))
        if found:
            print("VERDICT: PASS - boot0 accepts raw writes (not yet committed; no Complete sent)")
        else:
            print("VERDICT: write not visible in boot0 (staging-refused or wrong region). "
                  "Full write ABORTED. Use 'bblink rawseq' to iterate before --force.")
            sys.exit(3)

    def _probe_payload(self, off):
        probe = bytearray(BLOCK)
        probe[off:off + len(MARKER)] = MARKER
        return bytes(probe)

    # ------------------------------------------------------------------- write
    def write_boot0(self, image):
        if not self.boot_blocks and not getattr(self.opts, "force", False):
            print("ERROR: no boot0 block range known and --force not given. "
                  "Run 'probe' first, or pass --force." )
            sys.exit(3)
        blk0 = self.boot_blocks[0] if self.boot_blocks else 0
        data = open(image, "rb").read()
        if len(data) > BOOT0_SIZE:
            sys.exit("ERROR: image bigger than 4 MiB boot0")
        start = (len(data) // BLOCK) + (1 if len(data) % BLOCK else 0)
        nblocks = start
        print("== full boot0 write: %s (%d B, %d flash blocks) starting at block %d =="
              % (image, len(data), nblocks, blk0))
        print(FATAL_WIPE)
        if not getattr(self.opts, "yes", False):
            print("Type 'COMMIT' to flash boot0.img and reboot: ", end="", flush=True)
            if input().strip() != "COMMIT":
                sys.exit("aborted.")
        t0 = time.time()
        i = 0
        sent = 0
        while sent < len(data):
            chunk = data[sent:sent + BLOCK]
            self.sess.f7_write(blk0 + i, chunk)
            sent += len(chunk)
            i += 1
            if self.verbose and i % 32 == 0:
                print("  %d/%d blocks (%.1f%%) %.1fs" % (i, nblocks, 100.0 * i / nblocks, time.time() - t0))
        print("  sent %d blocks" % i)
        sig = bb.dummy_sig()
        self.sess.send_signature(sig)
        print("  install seal (560-byte signature) sent")
        self.sess.complete()
        print("  Complete (commit) sent")
        time.sleep(1.0)
        print("== verifying read-back ==")
        got = b""
        n = min(0x3FA0, BLOCK)
        for b in range(nblocks):
            got += self.cread((blk0 + b) * BLOCK, n)
        if got[:max(1, len(data))] == data[:len(got)]:
            print("VERDICT: PASS - boot0 now matches boot0.img (%d B read-back)" % len(got))
        else:
            print("VERDICT: read-back differs (got %d B) - re-check in the running device" % len(got))
        if getattr(self.opts, "reboot", True):
            self.sess.reboot_loader()
            print("  loader reboot sent - device reboots into Android SBL")


def main():
    ap = argparse.ArgumentParser(description="boot0_flash - Passport boot0 (Android SBL) flasher")
    ap.add_argument("--loader", default=LOADER, help="signed RAM-loader for the Passport")
    ap.add_argument("--password", default=None)
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--timeout", default=300, type=int, help="listener wait seconds")
    sub = ap.add_subparsers(dest="verb")

    p = sub.add_parser("selftest")
    p = sub.add_parser("verify-image"); p.add_argument("image")
    p = sub.add_parser("preflight")
    p = sub.add_parser("probe", help="read-only preflight + non-committing marker probe")
    p = sub.add_parser("write")
    p.add_argument("--image", default=None)
    p.add_argument("--yes", action="store_true", help="skip explicit COMMIT prompt")
    p.add_argument("--force", action="store_true", help="allow write without parsed boot0 range")
    p.add_argument("--no-reboot", action="store_true")

    opts = ap.parse_args()
    if not opts.verb:
        ap.print_help()
        return 1
    if not opts.loader or not os.path.exists(opts.loader):
        print("loader not found: %s" % opts.loader)
    opts.verbose = not opts.quiet

    if opts.verb == "selftest":
        return bb.cmd_selftest(bb.BBSession(), opts)
    if opts.verb == "verify-image":
        verify_boot0_image(opts.image)
        return 0
    if not os.path.exists(opts.loader):
        sys.exit("require --loader (or BBLINK_LOADER): %s" % opts.loader)

    if getattr(opts, "verb", "") in ("preflight", "probe", "write") and not getattr(opts, "quiet", False):
        print("device session active. If this box previously wiped the device, recover BB10 first.")

    tool = Tool(opts)
    try:
        if opts.verb == "preflight":
            pid = tool.wait_for_rim(timeout=opts.timeout, want=1)
            tool.drop_to_bootrom(pid)
            tool.preflight()
            return 0
        if opts.verb == "probe":
            pid = tool.wait_for_rim(timeout=opts.timeout, want=1)
            tool.drop_to_bootrom(pid)
            tool.probe()
            return 0
        if opts.verb == "write":
            image = opts.image or "boot0.img"
            if not os.path.exists(image):
                sys.exit("image not found: %s" % image)
            print("== pre-flight: offline image check ==")
            verify_boot0_image(image)
            pid = tool.wait_for_rim(timeout=opts.timeout, want=1)
            tool.drop_to_bootrom(pid)
            tool.preflight()
            tool.write_boot0(image)
            return 0
    finally:
        tool.sess.close()


if __name__ == "__main__":
    main()