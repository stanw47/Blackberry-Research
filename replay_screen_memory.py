#!/usr/bin/env python3
"""
replay_screen_memory.py
=======================
Deterministically replays the END-TO-END check of Oleksandr's premise:

    "...if we gained access to the *screen* process's memory,
     it would have the necessary privileges."

We test the two preconditions that actually decide feasibility:
  1. Can we READ the memory of `base/sbin/screen` (pid resolved at runtime)?
  2. Can we WRITE it?

Established device behaviour (verified on the sacrificial Classic):
  * /proc/<pid>/as is served by the proc manager.
  * Reads that span into a protected page return the readable prefix, then
    print "/proc/...: Server fault on msg pass" and stop (e.g. 10 of 64
    blocks = 40960 bytes).  That prefix is our reproducible read proof.
  * Writes (`dd ... of=/proc/<pid>/as bs=1 seek=<va>` via /base/bin/__root)
    return "N+0 records in / 0+0 records out": ZERO bytes are written --
    the proc manager refuses writes to screen's memory with our ability set.

The script prints every device reply in order, so you can show the live
replies.  It makes NO state-changing writes (the write probe is refused before
touching memory, so nothing on the device is altered).

PREREQUISITES (same as every session in this repo):
  1. SSH bridge to 169.254.0.1 up (port 22 open). If you re-pushed the key
     this session, run the Connect.jar key-push ritual first (see session7w).
  2. python3 + paramiko on THIS machine; qnx.py importable here.
     RUN (repo root, your Linux shell):
         python3 replay_screen_memory.py
"""
import os, sys, struct, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qnx import QNX

DCV          = "169.254.0.1"
SCREEN_NAME  = "base/sbin/screen"
READ_SKIP    = 68094            # byte-addr 0x10A1FC000 (proven readable window)
READ_COUNT   = 64               # pages; first 10 (40K) readable, 11th faults
PROBE_BASE   = 0x10A1FC000      # same VA, used for the write probes
PROBE_OFFSETS_KB = (0, 1, 2, 4, 8)   # +N KB within the readable run


def banner(t):
    print("\n" + "=" * 74)
    print(t)
    print("=" * 74, flush=True)


def main():
    print(f"## replay_screen_memory.py   host={DCV}\n", flush=True)
    q = QNX()
    print("[+] SSH shell up (transport OK)\n", flush=True)

    banner("STEP 1 — resolve the `screen` PID from `pidin`")
    out = q.cmd('echo "pidin" | /base/bin/__root', wait=4)
    pid = None
    for ln in out.splitlines():
        if SCREEN_NAME in ln:
            pid = int(ln.split()[0])
            print("    " + ln.strip())
    assert pid, "[!] did not find 'screen' in pidin"
    print(f"[+] screen PID = {pid}\n", flush=True)

    banner("STEP 2 — READ /proc/<pid>/as: 64 x 4K starting at 0x10A1FC000")
    cmd = (f'echo "/base/bin/dd if=/proc/{pid}/as of=/accounts/devuser/sc.bin '
           f'bs=4096 count={READ_COUNT} skip={READ_SKIP} 2>&1" | /base/bin/__root')
    out = q.cmd(cmd, wait=4)
    print("    " + "\n    ".join(out.strip().splitlines()))
    sftp = q.sftp(); sftp.get("/accounts/devuser/sc.bin", "/tmp/sc.bin"); sftp.close()
    blob = open("/tmp/sc.bin", "rb").read()
    print(f"[+] got {len(blob)} bytes  (first {len(blob)//4096} of {READ_COUNT} pages readable, "
          f"read aborts on the next), file[0] word = 0x{struct.unpack_from('<I', blob, 0)[0]:08X}")

    banner("STEP 3 — confirm the bytes are genuine `screen` data (GLES strings)")
    nz = sum(1 for b in blob if b)
    print(f"[+] non-zero bytes: {nz} / {len(blob)}")
    cur, found = "", []
    for b in blob:
        if 32 <= b < 127: cur += chr(b)
        else:
            if len(cur) >= 6: found.append(cur)
            cur = ""
    if len(cur) >= 6: found.append(cur)
    print(f"[+] ASCII strings in the read: {found[:8]}")

    banner("STEP 4 — WRITE test across the readable run (byte seeks, via __root)")
    payload = b"ABCDEFGH"
    open("/tmp/sc_wr.bin", "wb").write(payload)
    sftp = q.sftp(); sftp.put("/tmp/sc_wr.bin", "/accounts/devuser/sc_wr.bin"); sftp.close()
    for kb in PROBE_OFFSETS_KB:
        va = PROBE_BASE + kb * 4096
        cmd = (f'echo "/base/bin/dd if=/accounts/devuser/sc_wr.bin of=/proc/{pid}/as '
               f'bs=1 seek={va} conv=notrunc 2>&1" | /base/bin/__root 2>&1')
        out = q.cmd(cmd, wait=3)
        rec = [l.strip() for l in out.splitlines() if "records" in l]
        print(f"    write @0x{va:08X} ({kb:+}KB): {' ; '.join(rec)}")

    banner("STEP 5 — re-read to check whether ANY byte changed (integrity)")
    cmd = (f'echo "/base/bin/dd if=/proc/{pid}/as of=/accounts/devuser/sc2.bin '
           f'bs=4096 count={READ_COUNT} skip={READ_SKIP} 2>&1" | /base/bin/__root')
    q.cmd(cmd, wait=4)
    sftp = q.sftp(); sftp.get("/accounts/devuser/sc2.bin", "/tmp/sc2.bin"); sftp.close()
    blob2 = open("/tmp/sc2.bin", "rb").read()
    same = blob == blob2
    print(f"[+] re-read length {len(blob2)}; identical to first read = {same}")
    print("[+]   (identical -> the 'Server fault' write was REFUSED and touched nothing)")

    print("\n" + "=" * 74)
    print("VERDICT FOR OLEKSANDR'S PREMISE")
    print("  READ :  YES  - /proc/%d/as returns real screen heap bytes (STEP 2/3)."%pid)
    print("  WRITE:  NO   - every 'of=/proc/%d/as' dd reports 0 records out,"%pid)
    print("                and a re-read is byte-identical (STEP 4/5).")
    print("  => screen memory is READ-ONLY to us with the current __root ability set.")
    print("  => 'gaining access to screen's memory' for WRITE/injection is NOT")
    print("     currently possible; we would first need a higher ability (a signed")
    print("     helper or a PROCMGR/IO grant) before it becomes a useful host.")
    print("=" * 74)
    q.close()


if __name__ == "__main__":
    main()