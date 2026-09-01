================================================================================
SESSION 7G - LIVE DEVICE RECON + 3-OUTCOME STRATEGY - 2026-08-29
================================================================================
Device connected (adb, 0fca:8032), serial 1161797525, AAW068/venicena, SELinux
enforcing, shell = uid 2000 u:r:shell:s0, CapEff=0 CapBnd=0xc0.

[1] LIVE CONFIRMATIONS (theory -> fact)
  - /dev/pathtrust EXISTS: crw-rw-rw- (666, world-openable) root root,
    label u:object_r:pathtrust_device:s0. Shell can OPEN it (read -> EINVAL,
    not EACCES). /sys/kernel/pathtrust + /proc/pathtrust do NOT exist.
  - /dev/bide: Permission denied to shell (ls -laZ fails) -> UID-gate confirmed.
  - MNT_TRUSTED mounts (from /proc/self/mountinfo): ONLY these have "trusted":
      / (rootfs) ro,trusted
      /system  dm-0 ro,trusted   (dm-verity)
      /oem     dm-1 ro,nosuid,nodev,trusted  (dm-verity)
    NOT trusted: /data (dm-2, forceencrypt), /cache, /persist, /firmware,
    /nvram/* (fuse). => Pathtrust enforcement: root/banned-caps/forbidden-sid
    cannot exec/mmap-exec/insmod/request_fw from /data or anywhere non-trusted.
  - Binder services listed: #120 fidocryptodaemon, #121 drm.drmManager,
    #126 android.security.keystore. (Listed != reachable; per sepolicy only
    keystore is shell-callable, fidocryptodaemon/drm are NOT.)
  - NO microSD present: /proc/partitions shows only zram0 + mmcblk0 (eMMC,
    p1-p36); no mmcblk1. => "boot Linux from SD" needs an SD inserted AND an
    unlocked bootloader (kexec is NOT compiled in - no CONFIG_KEXEC).
  - pstore mounted at /sys/fs/pstore but Permission denied to shell.
  - Termux NOT currently installed (com.termux absent) - the earlier install
    was wiped by the full flash/restore.

[2] NEW BUG FOUND - Pathtrust fget refcount leak (security/pathtrust/ioctl.c)
  - pathtrust_cdev_ioctl() case IOCTL_TRUST_FILE:
        file = fget(value);              // increments file refcount
        ... if (file && !trusted && (root|banned|forbidden)) return -EPERM;
        return 0;                        // <- NO fput(file) on ANY path
  - grep -c "fget\|fput" ioctl.c == 1 (only the fget). => every IOCTL_TRUST_FILE
    call on a valid fd LEAKS a file reference. Reachable from shell (uid 2000):
    /dev/pathtrust is 666 and shell can open it; shell passes the (non-root,
    non-banned) branch so it leaks while returning 0.
  - Severity: LOW. It is a kernel object-pinning / memory-exhaustion leak (the
    file object can never be freed), NOT a use-after-free or write primitive.
    Reaching a UAF would require refcount wrap (2^64 calls, impractical). It is
    nonetheless a genuine BB code bug (missing fput), the first concrete kernel
    bug found in the BB-original code. Worth reporting/publishing.
  - NOTE: also observed a transient [BIDE] "report_dequeue rc=512" flood in
    dmesg (~t=1005-1028s after boot, then stopped) - BIDE report queue
    malfunction (ERESTARTSYS), likely JBIDE userspace briefly not draining.
    Benign but shows BIDE's report pipeline can stall.

[3] THREE-OUTCOME STRATEGY (dependency map)
  The three desired outcomes collapse to ONE dependency chain:

    ROOT is the linchpin. Both "flash a ROM" (software) and "boot full Linux"
    require root (for hlos_unsigned.tkn write, or kexec). And root is the only
    goal with NO public solution.

  OUTCOME 1 - ROOT (software): only a novel kernel 0-day. Active thread = session
    7A binder UAF->pipe writev (stalled on kmalloc-512 slab reuse). Other seams:
    keystore binder (shell-reachable, but hardened), widevine trustlet underflow
    (needs prior foothold). All long-shots. NOTE: GRSEC PAX_REFCOUNT=y kills
    refcount-spray; Pathtrust+BIDE don't add blockers for a kernel WRITE
    primitive (they only gate post-exploitation actions).

  OUTCOME 2 - FLASH ROM (LineageOS/Graphene): requires bootloader unlock =
    hlos_unsigned.tkn with state=development in /nvram/nvuser = requires ROOT
    (write gate) OR the HARDWARE route (balika eMMC swap, the ONLY proven unlock).
    GrapheneOS note: it does NOT support the Priv/msm8992 at all (Graphene is
    Pixel-only) - LineageOS 18.1 (balika's build) is the only realistic ROM.

  OUTCOME 3 - "RUN SOMETHING ON TOP" / boot Linux from SD:
    - kexec: NOT compiled (no CONFIG_KEXEC) -> cannot hot-replace kernel.
    - boot from SD: no mmcblk1 present AND needs unlocked bootloader anyway.
    - ACHIEVABLE NOW (no root): Termux + proot = full Debian/Ubuntu USERSPACE
      running on Android's kernel, inside the sandbox. Limited (no kernel, no
      raw block devices, no dm-verity bypass) but it is real Linux-on-top.
    - After root (if ever): chroot + raw block access + (no kexec, so no new
      kernel) - still can't boot a new kernel, only userspace.

  HONEST RANKING (probability x value):
    1. HARDWARE eMMC swap (balika/imggen) - the ONLY proven path to root+ROM.
       High effort, destructive, but demonstrated once on a Priv.
    2. ROOT via kernel 0-day (7A) - long-shot, but if it lands it unlocks 1+2.
    3. Termux+proot (outcome 3) - immediate, no root, limited but real.

  RECOMMENDED NEXT ACTIONS (concrete):
    - If you want a win TODAY: reinstall Termux (the 24MB v0.119.0 beta APK from
      GitHub CI) + proot Ubuntu/Debian. I can drive this via adb.
    - If you want the real unlock: (a) reach balika/BBAndroids Discord for the
      exact eMMC-swap recipe + a donor 64GB chip, OR (b) continue the 7A kernel
      LPE with the slab-reuse fix (spray kmalloc-512 before/after the free).
    - Publish the Pathtrust fput leak + the BIDE detection-gap map (session 7E)
      - these are genuine contributions no one has posted.

ARTIFACTS: /home/stanw47/priv-research/kernel/bb_kernel_AAO474/ (source);
  sessions 7A-7G in /home/stanw47/priv-research/work/.
================================================================================
