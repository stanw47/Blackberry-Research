================================================================================
BUG REPORT - BlackBerry Pathtrust IOCTL_TRUST_FILE file reference leak
================================================================================
Date:        2026-08-29
Component:   BlackBerry Priv (STV100-1) kernel, AAW068 (msm8992, 3.10.84)
             security/pathtrust/ioctl.c  (in-tree GPL source, branch AAO474)
Reachable:   shell (uid 2000) - /dev/pathtrust is mode 0666, shell can open it
Severity:    LOW (kernel object leak / DoS; NOT a privilege-escalation primitive)

------------------------------------------------------------------------------
THE BUG
------------------------------------------------------------------------------
pathtrust_cdev_ioctl() handles IOCTL_TRUST_FILE (0x7000, _IOR('p',0,int)):

    case IOCTL_TRUST_FILE: {
        ...
        file = fget(value);                 // <-- increments file->f_count
        fsid = is_forbidden_sid(tsec->sid);

        if (file && !(file->f_path.mnt->mnt_flags & MNT_TRUSTED) &&
                (is_root(cred) || has_banned_caps() || fsid)) {
            ... audit ...
            return -EPERM;                  // <-- no fput(file)
        }
        return 0;                           // <-- no fput(file)
    }

  fget() takes a reference on the struct file identified by 'value' (an fd).
  NO code path calls fput(). The reference is therefore never released.

  Static confirmation: `grep -c "fget\|fput" ioctl.c` == 1 (only the fget).

------------------------------------------------------------------------------
TRIGGER
------------------------------------------------------------------------------
  fd = open("/dev/pathtrust", O_RDWR);           // succeeds as shell (0666)
  victim = open("/data/local/tmp/x", O_RDWR);    // any fd we own
  ioctl(fd, IOCTL_TRUST_FILE, victim);           // leaks one ref on 'victim'

  (shell takes the "return 0" branch: not root, no banned caps, sid not in the
   forbidden list - so it leaks while returning success.)

------------------------------------------------------------------------------
WHAT IT IS / IS NOT
------------------------------------------------------------------------------
IS:
  - A genuine memory-management bug (missing fput) in BlackBerry's own code.
  - A kernel object-pinning primitive: a struct file (and transitively its
    dentry/inode/page-cache) can be kept alive after its fd is closed.
  - A slow resource-exhaustion DoS if repeated across many distinct files.

IS NOT:
  - NOT a use-after-free. The leak keeps an object alive (free too LATE), the
    opposite direction from UAF.
  - NOT an overflow-to-UAF. struct file->f_count is atomic_long_t (64-bit);
    wrapping it to 0 needs 2^64 calls (~584,000 years at 1M/s). Impractical.
  - NOT an efficient memory leak. fget() does not allocate; leaking N refs on
    the SAME file only increments a counter on ONE object. To consume real
    memory you must open+leak many DISTINCT files, bounded by fd limits.
  - NOT an info leak. The ioctl returns only 0/-EPERM; it never copies kernel
    data to userspace (despite the _IOR direction).

------------------------------------------------------------------------------
POTENTIAL (SPECULATIVE) CHAINS
------------------------------------------------------------------------------
  The leak is only useful as a COMPONENT of a larger chain, e.g.:
  1. Pin a file whose ->release has a security side-effect so it is skipped.
  2. Keep a dentry/inode/page-cache alive to control heap layout (grooming)
     for an unrelated overflow/UAF bug.
  3. Cross-file refcount accounting bug if another driver checks f_count.
  None of these is exploitable on its own; each requires a second bug.

------------------------------------------------------------------------------
WHY THIS MATTERS
------------------------------------------------------------------------------
  1. It is the first concrete bug found in BlackBerry's OWN kernel code,
     and it was found in the FIRST file we deep-audited (ioctl.c). That is
     evidence the "defensive BB code" hypothesis is not absolute - there are
     oversights, which justifies auditing the remaining unread files.
  2. It is independently reportable (a real finding vs. the shipped EOL
     device; BB will not patch it, but it belongs in the public record).
  3. It maps a NEW attack surface: /dev/pathtrust is 0666 and shell-openable,
     which is not obvious from the SELinux label alone.

------------------------------------------------------------------------------
UNREAD / NEXT AUDIT TARGETS (higher-value than this bug)
------------------------------------------------------------------------------
  - security/pathtrust/pathtrustfs.c   (343 lines, trusted-filesystem interface)
  - drivers/bide/bide_tz.c             (709 lines, TrustZone comms framing)
  - drivers/bide/bide_util.c           (341 lines, get_user_pages on task mm)
  - drivers/bide/bide_caps.c           (311 lines, capability list)
  - drivers/bide/bide_hash.c           (298 lines, custom rbtree hash)
  - drivers/bide/bide_secop.c          (module_phys_mem under AVEN_44469_FIXED)
================================================================================
