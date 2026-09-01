================================================================================
SESSION 7I - VTNVFSD RE (nvuser on-disk format) + EMMC/ISP STRATEGY - 2026-08-29
================================================================================
Goal: determine the raw nvuser on-disk layout for a .tkn file (so an ISP write
of hlos_unsigned.tkn would be accepted by aboot).

[1] VTNVFSD = a FUSE filesystem over a BLOCK-BASED on-disk format
  Binary: priv-research/fw/bin_vtnvfsd (aarch64, 115KB, stripped, links BB "sbg"
  crypto lib + ss_read_proc_id QSEE call).
  Driver fns: vtnvfs_{mount,format,write,read,remove,getstats}_drv.
  Key facts from strings + disasm:
    - Block-based: "not enough block %u, need at least 3";
      "File length + name length is too long, would occupy more than %d blocks";
      "fs is full, could not get %d blk".
    - Per-file HEADER with a length field: "malformed header: len=%zu, hdr->len=%u"
      (read path validates each header's len).
    - Hash-based file lookup: "HASH COLLISION %u", "SECOND VALIDATE %u" -> a
      32-bit hash keyed table (like bide_hash.c), with collision handling.
    - Token files: regex ".*\.tkn$"; signature sidecar name ".sig.%s";
      "%s signature verification failed" -> vtnvfsd VERIFIES .tkn signatures
      (sbg ECDSA/RSA + ss_read_proc_id) on the OS write/read path.
    - Exact block size + header field offsets still TBD (needs a nvuser dump or
      more RE). Block size candidates: 512/4096.

[2] THE KEY INSIGHT - aboot does NOT verify the token signature
  - vtnvfsd (OS layer) verifies .tkn signatures -> this is what stops unpriv
    writes via the filesystem ("zztest.tkn rejected by vtnvfsd sig-check", log 6C).
  - aboot (bootloader, session 3/6D RE) reads /nvuser/hlos_unsigned.tkn and only
    checks state=="development"; NO signature check.
  => An ISP write that lays the 96-byte token into nvuser in the RAW vtnvfs
     block format (name "hlos_unsigned.tkn", payload 'state="development"',
     NO .sig sidecar needed) should be accepted by aboot, bypassing vtnvfsd's
     sig check entirely. The remaining work is ONLY the exact block/header bytes.

[3] REMAINING TO NAIL THE FORMAT (ranked)
  1. Obtain a nvuser dump (ideal): rooted Passport/Classic can dump ITS OWN
     nvram, but not the Priv's nvuser. Priv nvuser dump needs root or ISP.
  2. Finish vtnvfsd RE: extract block size (mount/format_drv) + header struct
     (read_drv). Deterministic but time-consuming.
  3. Cross-check aboot's token-reader (already RE'd session 3) to confirm the
     exact fields it parses (state offset within the token blob).

[4] QUESTION: easier to flash a custom image on ROOTED Classic/Passport?
  Depends on what "custom image" means:
  A. DIFFERENT BB10 autoloader (downgrade): YES easier with root. The
     Impersonation (/q/) layer's `mod_nvram -d` deletes the DOWNGRADE BLOCKLIST,
     allowing any autoloader flash. (Their devices run getroot, NOT
     Impersonation, so they need the Impersonation autoloader for this.)
  B. ANDROID/LINAGEOS (Balika conversion): NO, root does NOT help. Balika =
     desolder + edit phyboot0/HWI (bbss.insecure=true) + imggen boot0/boot1
     rewrite. That is an eMMC write-protect bypass, INDEPENDENT of userland
     root. getroot gives userland root (root sshd, file access) but NOT the
     ability to write the eMMC boot0 region.
  C. THE BIG OPPORTUNITY the rooted devices DO provide: with root SSH on the
     Passport/Classic, you can DUMP the full eMMC (boot0/boot1/HWI/nvram) via
     the running OS - NO desolder needed. This gives you the exact HWI layout,
     the bbss.insecure location, and the boot0/boot1 format to plan a precise
     ISP (or software, if WP is toggleable) write. It turns the Balika method
     from "blind desolder" into a fully-informed write.

[5] STRATEGIC SYNTHESIS (3 outcomes, revised with eMMC/ISP lens)
  - Priv: ISP token-write is the theoretical software-free unlock (write
    hlos_unsigned.tkn state=development into nvuser). Gated only by (a) ISP
    hardware + test points, (b) the vtnvfs raw layout (session 7I in progress).
    User prefers NOT to open the Priv, so this is a last resort.
  - Classic/Passport: already rooted. Highest-value moves:
      1. Dump full eMMC via root SSH (understand HWI/boot0 exactly).
      2. Determine if boot0 is software-writable with root (test ext_csd WP
         toggle / raw block write on the QNX device).
      3. If boot0 writable -> apply Balika imggen WITHOUT desolder (the win).
         If not -> use the dump to plan a precise ISP write.
      4. Separately: get the Impersonation autoloader (/q/) for mod_nvram -d
         downgrade capability.
  - The rooted devices are the BEST current leverage: they let us replicate the
    Balika method with full information, and possibly without removal if boot0
    is software-writable.

ARTIFACTS: vtnvfsd binary + disasm in priv-research/fw/; this note; source in
  priv-research/kernel/bb_kernel_AAO474/.
================================================================================
