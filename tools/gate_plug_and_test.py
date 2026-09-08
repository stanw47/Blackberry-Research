#!/usr/bin/env python3
"""
gate_plug_and_test.py - fused EDL boot0-write gate test.

The device only stays in BootROM for a few seconds after plug-in, so the host
must be LISTENING first and fire the handshake the instant PID 0x0001 appears.

Flow:
  1. tight USB poll for VID 0x0FCA (any RIM device)
  2. the moment it appears -> full bring-up to RAM-loader (connect)
  3. preflash(0x15) for the Classic
  4. F7 write of a probe block containing CLSCMRKR at boot0 sector 2048
  5. CREAD read-back from the same location to see if it landed
No Complete is sent: single-point addressability probe, non-committing.
"""
import sys, os, struct, time
import usb.core

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bblink as bb
import run_boot0_marker_test as gate

MARKER_OFFSET = gate.MARKER_OFFSET
MARKER = gate.MARKER


def wait_for_rim(timeout=180):
    print(">>> WAITING for RIM USB device. PLUG THE PHONE IN NOW <<<", flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout:
        dev = usb.core.find(idVendor=bb.VID_BB)
        if dev is not None:
            pid = int(dev.idProduct)
            print("FOUND PID=0x%04X" % pid, flush=True)
            return pid
        time.sleep(0.02)
    print("TIMEOUT waiting for device", flush=True)
    sys.exit(2)


def drop_to_bootrom(sess, opts, pid):
    """Mirrors bb10mt ConnectToBB: if the device is in the OS-session PID
    (0x8017), open it and send the channel0 cmd=3 reboot to force BootROM."""
    if pid in (1, 0x8001):
        return True
    print("PID=%04X is OS-session; sending session reboot to drop to BootROM"
          % pid, flush=True)
    try:
        if sess._open_pid(pid, timeout=8000):
            sess.session_reboot()
    except Exception as e:
        print("reboot failed: %s" % e, flush=True)
    sess.close()
    time.sleep(2.5)
    return True


def main():
    class O:
        def __init__(s, **k):
            s.__dict__.update(k)
    opts = O(loader=gate.LOADER, password=None, verbose=True)

    pid = wait_for_rim()

    sess = bb.BBSession(verbose=True)
    try:
        drop_to_bootrom(sess, opts, pid)
        bb.connect(sess, opts)
        sess.preflash(0x15)
        print("preflash(0x15) ok", flush=True)

        block_num, in_block = gate.boot_block_number(MARKER_OFFSET)
        probe = bytearray(bb.BLOCK)
        probe[in_block:in_block + len(MARKER)] = MARKER
        t0 = time.time()
        ok = sess.f7_write(block_num, bytes(probe))
        print("F7 write of probe block returned ok=%s (%.2fs)"
              % (ok, time.time() - t0), flush=True)
        print("!! boot0 address WRITE acknowledged by RAM-loader" if ok
              else "F7 write NOT acknowledged - boot0 write refused", flush=True)

        sess.cread_init()
        n = min(0x3FA0, bb.BLOCK)
        r = sess.cread(block_num * bb.BLOCK + in_block, n)
        found = MARKER in r
        print("CREAD read-back: found=%s bytes=%d" % (found, len(r)), flush=True)
        if found:
            print("VERDICT: PASS - boot0 write lands (no Complete sent yet)", flush=True)
        else:
            print("VERDICT: write ACK but read-back clean (not committed "
                  "without Complete) or write never landed", flush=True)
    finally:
        sess.close()


if __name__ == '__main__':
    main()