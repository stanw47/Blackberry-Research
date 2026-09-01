================================================================================
SESSION 7C - BLACKBERRY KERNEL SOURCE ANALYSIS (BB "engineering map") - 2026-08-29
================================================================================
Goal: use BlackBerry's OWN released source + config to map what their engineers
actually built/hardened, and find BB-original attack surface.

SOURCE AVAILABILITY (GPL release, github.com/blackberry/android-linux-kernel):
  - Repo archived 2026-03-20. Branch naming [platform]/[build].
  - msm8992 has EXACTLY 60 branches: AAC724 ... AAO486 (AAB..AAO; AAM absent).
  - CRITICAL: our build AAW068 is NOT published. Latest released = AAO486
    (VZW); AAO474/AAO484/AAO486 are the newest. So the EXACT AAW068 kernel
    source does not exist publicly (GPL gap). AAO474 is the closest proxy.
  - Cloned shallow: /tmp/opencode/bb_kernel_AAO474 (branch msm8992/AAO474).
  - AAO474 Makefile VERSION=3.10.84 == our running kernel 3.10.84-perf-gd46863f.

GRSECURITY/PaX: full source IS in-tree under grsecurity/ (NOT redacted):
  grsec_mem.c, grsec_pax.c, grsec_ptrace.c, grsec_tpe.c, grsec_usb.c,
  gracl_*.c (RBAC), grsum.c, Kconfig, etc.

EXACT KERNEL CONFIG (arch/arm64/configs/bbryqc8992_defconfig) - EXPLOIT MITIGATIONS:
  CONFIG_PAX=y
    PAX_NOEXEC=y, PAX_PAGEEXEC=y          (PAGEEXEC on - matches log "Pemrs")
    PAX_USERCOPY=y                         (usercopy protection)
    PAX_REFCOUNT=y                         (refcount overflow protection ->
                                             blocks CVE-2016-3842/13905/5831,
                                             binder kref/UAF refcount spray)
    PAX_ASLR=y, RANDMMAP=y, RANDUSTACK=y
    PAX_MEMORY_UDEREF=n, PAX_KERNEXEC=n    (NO SMAP/SMEP-style kernel guard)
    PAX_MEMORY_SANITIZE=n, STRUCTLEAK=n, CONSTIFY=n
  CONFIG_GRKERNSEC=y
    GRKERNSEC_NO_RBAC=y                    (gracl RBAC COMPILED OUT)
    GRKERNSEC_KSTACKOVERFLOW=n             (NO kernel stack-overflow detection)
    GRKERNSEC_HARDEN_PTRACE=n              (ptrace hardening OFF in GRSEC)
    GRKERNSEC_PTRACE_READEXEC=y
    GRKERNSEC_PROC_MEMMAP=n
    GRKERNSEC_PERF_HARDEN=y, BLACKHOLE=y, DMESG=n
  CONFIG_DEBUG_LIST=n                       (no list poisoning / DEBUG_LIST)
  CONFIG_BBRY_BIDE=y                        (BlackBerry Integrity Detection)

  => DISCREPANCY worth chasing: GRSEC HARDEN_PTRACE=n and PROC_MEMMAP=n, yet
     the device empirically blocks ptrace(ATTACH) and /proc/self/mem writes
     (session 4/7). => BlackBerry added their OWN patches ON TOP of GRSEC for
     those. This is the "belt-and-suspenders" layer the log has been seeing.
  => KSTACKOVERFLOW=n + DEBUG_LIST=n means kernel stack overflows and list
     corruption are NOT detected at runtime (no guard page, no poisoning) -
     relevant if a BB driver has a stack overflow or list bug.

BLACKBERRY-ORIGINAL ATTACK SURFACE (the "what BB engineers wrote" answer):
  1) drivers/bide/  = BIDE (BlackBerry Integrity Detection Engine) - BB's OWN
     kernel security subsystem. A kernel<->TrustZone bridge. Files:
       bide_{module,dev,ctl,netlink,tz,tlv,xml,crypto,hash,auth,caps,secop,
       thread,report,vma,util}.c + tzbb_protocol_public.h
     - /dev/bide char device. fops: unlocked_ioctl/compat_ioctl/read/write/open.
     - dev_open -> dev_check_access(): UID gate. Allows only BIDE_UID (BB
       reserved), ROOT_UID(0), SYSTEM_UID(1000). shell(2000) DENIED.
     - ioctl surface (dev_ioctl): per-command -EPERM checks; auth_add_pid()
       grants AUTH_PERM_* (PRIVELEGED_CHILDREN, INSTALLD, ZYGOTEMGR,
       PRIVILEGED_GID, SYSTEM_UID, PRIVILEGED_LINEAGE, PRIVILEGED_ZYGOTE,
       BUGREPORT); caps_add_process(prog_name,...); snapshot/sign cmds.
     - TrustZone commands (tzbb_protocol_public.h): TZ_CMD_BIDE_ADD_SECTION(2000),
       GENERATE_KEYPAIR(2001), SIGN_DATA(2002), GENERATE_NONCE(2003),
       REMOVE_SECTION(2004). Crypto: ECC256/521, AES128, SHA256/512, HMAC.
       Section hashing in TZ with TZ_SECTION_FLAG_REMOVABLE.
     - netlink (bide_netlink.c) peers: NETLINK_QSEECOM, NETLINK_PATHTRUST,
       NETLINK_SELINUX. TLV parser (bide_tlv.c), XML parser (bide_xml.c),
       VMA walking (bide_vma.c) for hashing memory regions.
     => BIDE is a THIRD security layer on top of GRSEC + SELinux. Its parsers
        (TLV/XML) + netlink + ioctl are BB-original code = prime bug-hunting
        ground IF a system/BIDE_UID context is ever obtained (or a uid gate
        bypass found).
  2) BB custom drivers (device-facing, lower value): drivers/input/misc/bbry/*
     (sensor hub: hall, l3gd20, lsm303d, m4_hub, stmvl6180),
     drivers/input/touchscreen/synaptics_dsx_bbry/* (incl. DDT fw update),
     stmpe-keypad-bbry.c, msm8992-pm8994-bbry-venice*.dts{i}.
  3) kernel_defconfig.py = BB's own defconfig build tool (merge/overlay).

STRATEGIC TAKEAWAYS:
  - BB's defense = GRSEC/PaX (in-tree) + SELinux (enforcing) + BIDE (runtime
    integrity + process authorization) + boot-chain ECDSA + dm-verity. FIVE
    independent layers, all on. This is why no public root exists.
  - BB-original code (BIDE) is the highest-value BB-written attack surface: it
    parses TLV/XML, walks VMAs, speaks netlink + TZ. Not in prior log.
  - To reach BIDE you already need uid 0/1000/BIDE_UID -> circular, but the
    kernel-exploit path (PAX_REFCOUNT=y, KSTACKOVERFLOW=n, DEBUG_LIST=n) and
    the netlink families (PATHTRUST/QSEECOM) are worth separate RE.
  - Next concrete RE targets: bide_netlink.c (netlink msg parsing + sender
    filtering), bide_tlv.c, bide_xml.c (parser bugs), and the NETLINK_PATHTRUST/
    NETLINK_QSEECOM families (userspace reachability).

ARTIFACTS:
  - DURABLE CLONE (complete working tree, 778M):
    /home/stanw47/priv-research/kernel/bb_kernel_AAO474/   (branch msm8992/AAO474)
  - (old /tmp clone removed; /tmp freed.)

------------------------------------------------------------------------------
COMPLETE BLACKBERRY KERNEL SECURITY ARCHITECTURE MAP (from source)
------------------------------------------------------------------------------
CONFIG flags (bbryqc8992_defconfig): BBRY, BBRY_HWFEATURES, BBRY_PERSIST_RESET_V2,
  BBRY_BSI (PMIC battery interface), BBRY_DDT, BBRY_BIDE, BBRY_MASKED_IP_BOOST,
  SECURITY_PATHTRUST (+ROOTFS/BOOTPARAM/SELINUX sub-flags).

Security LAYERS (6, all on):
  1. Boot chain (ECDSA verified boot, aboot->SBL etc.)  [userspace]
  2. GRSEC/PaX (grsecurity/ in-tree, full source)
  3. SELinux (enforcing, no permissive)
  4. PATHTRUST  = SECOND LSM (security/pathtrust/) - trusted executable-path +
     mount-device enforcement. Hooks: bprm_set_creds, sb_mount, sb_kern_mount.
     /dev/pathtrust char dev + IOCTL_TRUST_FILE. netlink.c (NETLINK_PATHTRUST,
     PTNLGRP_ALL). pathtrustfs.c. toggled by pathtrust_enforce. Whitelist:
     /data/dalvik-cache/*/boot.oat + *@classes.dex (PATHTRUST_PATHNAMES).
  5. BIDE (drivers/bide/) = BlackBerry Integrity Detection Engine - TZ bridge,
     /dev/bide (UID-gated), TLV/XML parsers, reports incidents (SN_*).
  6. dm-verity (/system + /oem)  [userspace]

BLACKBERRY-ORIGINAL KERNEL CODE (the "what BB engineers wrote" map):
  - drivers/bide/            (20 files) integrity detection + TZ comms + crypto
  - security/pathtrust/      (7 files) 2nd LSM, /dev/pathtrust, netlink
  - drivers/staging/bbry/    ddt.c (Device Diagnostic Tools), debug_extra.c
                             (ro.boot.debug_extra=1 -> suid_dumpable), export_bsi.c
                             (sysfs BSI blob, mfg), hwfeatures.c (dt hwfeature sysfs),
                             reset_region_v2.c (persist reset logs)
  - drivers/input/misc/bbry/*        sensors (hall/gyro/mag/hub/prox)
  - drivers/input/touchscreen/synaptics_dsx_bbry/*  touch + DDT fw update
  - drivers/net/wireless/bcmdhd_*/wlan_ddt/*        wifi DDT

BIDE NETLINK = kernel-internal listener ONLY (subscribes to NETLINK_SELINUX/
  NETLINK_PATHTRUST/NETLINK_QSEECOM broadcast groups; reacts to setenforce=0,
  pathtrust disable, qseecom init). NOT a userspace send target. So BIDE's
  userspace-facing surface = /dev/bide ioctl (root/system/BIDE_UID only).

DETECTION SURFACE (what BIDE + pathtrust flag as incidents - matters for the
  "avoid detection" heist model):
  - SELinux setenforce(0)              -> SEVERITY_CRITICAL SN_SELINUX_DISABLED
  - SELinux policy reload (seqno!=1)   -> SN_SELINUX_CHANGED
  - Pathtrust disable (enforce=0)      -> SN_PATHTRUST_DISABLED
  => If a kernel exploit later calls setenforce(0), BIDE logs a CRITICAL
     incident to JBIDE/DTEK immediately. Worth knowing for stealth.

NEXT RE TARGETS:
  - bide_tlv.c / bide_xml.c parser audit (parse data from TZ/JBIDE).
  - bide_secop.c / bide_tz.c (TZ comms framing, section hashing).
  - Pathtrust: pathtrustfs.c + ioctl.c (IOCTL_TRUST_FILE) + selinux.c interplay;
    the /dev/pathtrust device gating (likely root/system, confirm).
  - debug_extra.c: is ro.boot.debug_extra ever settable from userspace?
  - bide_auth.c auth_add_pid() / AUTH_PERM_* flags (process authorization model).
================================================================================
