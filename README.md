# BlackBerry Research

Security research notes, reverse-engineering artifacts, and tooling for
BlackBerry 10 (BB10/QNX) and BlackBerry Android-era devices. **This is a
research aid, not a flashing guide.**

> **DISCLAIMER — READ THIS FIRST**
>
> This repository exists **purely as a research aid**. Nothing here is
> production code, a supported tool, or an officially endorsed procedure.
>
> - **Intended use is strictly educational and defensive security research** on
>   devices you legally own and are authorized to test.
> - **This can permanently brick your device.** Flashing, modifying the eMMC
>   boot partitions (`boot0`/`boot1`), changing `BOOT_WP`/`bbss.insecure`, or
>   writing the `ext_csd` can render a phone unbootable with **no recovery path
>   short of a JTAG/ISP chip-out and rework**.
> - **Unlocking the bootloader voids your warranty** and may violate the
>   terms of service you agreed to with the carrier or manufacturer.
> - **Use at your own risk.** The author(s) assume **no liability** for any
>   damage, data loss, bricked devices, or legal consequences arising from use
>   of this material.
> - Some artifacts reference **third-party proprietary firmware/bootloaders**
>   (BlackBerry, Qualcomm). See [LEGAL.md](LEGAL.md). They are provided only
>   where necessary to document findings, and only for research/compatibility
>   purposes.

---

## Table of contents

1. [Devices](#devices)
2. [What was attempted — full synopsis](#what-was-attempted)
3. [Where things stand per device](#where-things-stand)
4. [Key technical findings (pinned)](#key-technical-findings)
5. [Open leads / unexplored paths](#open-leads)
6. [Why certain approaches do or don't work](#why-doesn-t-it-work)
7. [Repository layout](#repository-layout)
8. [License / legal](#license)

---

## Devices

| Device | OS | SoC | Build / variant |
|---|---|---|---|
| **Classic** | BB10 / QNX | MSM8960 | `QNX BLACKBERRY-528E`, CLASSICNA |
| **Passport** | BB10 / QNX | MSM8974AA | `QNX BLACKBERRY-603C`, WINDERMEREEMEA |
| **Priv** | Android | MSM8992 | `AAW068`, venicena |

---

## What was attempted

The overarching goal was **bootloader unlock to run a custom OS (LineageOS)**
on the Classic/Passport, and **root / persistence** on all three. Everything
below was tried and is logged in [`notes/`](notes/).

### BB10 / QNX (Classic + Passport)

1. **Root via the `bb10.root.sx` "getroot" payload** — succeeded. The devices
   ship a pre-rooted autoloader whose `btool` script runs as root at boot via
   an `ota_info_pps.sh` symlink.
2. **Real interactive uid-0** — achieved by adding
   `/proc/boot/pathtrust !/base/bin/__root` to `btool` (line 31), causing the
   `__root` setuid helper to become path-trust-"trusted" on every boot.
3. **Raw eMMC read access without desoldering** — achieved via the setgid
   "group wrapper" `g_Disk_Drivers` (a procmgr-ability ksh wrapper), which
   grants the `Disk_Drivers` group and thus read/write to `/dev/emmc/*`.
4. **eMMC boot/secure partition dumps** — `boot0`, `boot1`, `nvram0`, `dmi0`
   recovered to `dumps/`.
5. **`bbss.insecure` flag pinning** — identified as build-info field8 (u32) at
   `boot0` offset `0x35a98` (currently `0` = secure), by decoding the public
   `imggen` toolchain.
6. **Bootloader-write attempt** — blocked. `boot0`/`boot1` are hardware
   write-protected (`EROFS` even as root); the user area (`uda0`/`os0`/`dmi0`)
   is writable.
7. **QNX MMC devctl reverse engineering** — decoded
   `DCMD_MMCSD_WRITE_PROTECT` (`0xC0201A11`), `DCMD_MMCSD_VUC_CMD`
   (`0xC0441A16`), `DCMD_MMCSD_CARD_REGISTER` (`0xC0181A14`) and the driver's
   internal dispatch table by reverse-engineering `sdmmc-rim-msmsdcc`.
8. **Live CMD6 SWITCH / write-protect toggle attempts** — `WRITE_PROTECT`
   returns `EIO`; `VUC_CMD` (raw command) returns `ENOTTY` (not implemented).
9. **`/proc/<pid>/as` memory patching** — established that the driver's
   `.data`/`.bss` is writable via `dd` on `/proc/as`, but `.text` is read-only
   ("Server fault on msg pass"), preventing a dispatch-table patch.
10. **`/dev/mem` physical-RAM audit (Passport)** — ruled out: the char device
    opens `O_RDWR` but serves a uniform `0xdeadbeef` canary at every address with
    no data persistence. See session10a.

### Priv (Android)

1. **Kernel source audit** — mapped BlackBerry's in-kernel security stack
   (grsecurity/PaX, BIDE, Pathtrust) from the published GPL source.
2. **BIDE / Pathtrust code audit** — full audit of the detection LSM (BIDE) and
   the enforcement LSM (Pathtrust); found several minor bugs but no
   unprivileged-privilege-escalation primitive.
3. **QSEE / trustlet surface audit** — enumerated the `qseecom`-capable
   SELinux domains and audited `vend_fidodaemon` / token-service.
4. **Reported bug** — a genuine `fget()`-without-`fput()` reference leak in
   `security/pathtrust/ioctl.c` (see
   [`notes/bug-report-pathtrust-fput-leak.md`](notes/bug-report-pathtrust-fput-leak.md)).

---

## Where things stand

- **Classic / Passport: fully rooted** (real uid-0). The bootloader unlock is
  **fully understood and pinned to a single byte** — but writing that byte is
  **hardware-gated** (boot-partition write-protect).
- **Priv: not rooted.** Requires a kernel 0-day (none public) or hardware
  (ISP) access to write `hlos_unsigned.tkn` to `nvuser` (which is *not*
  write-protected, unlike boot0 — so the Priv's equivalent step is easier to
  *write*, but its block devices are SELinux-gated and there is no
  `g_Disk_Drivers` equivalent).

---

## Key technical findings

These are the durable, pinned facts the research produced (all cross-referenced
in [`notes/`](notes/)).

1. **Real uid-0 root** on BB10 via the path-trust whitelist trick
   (`/proc/boot/pathtrust !/base/bin/__root`).
2. **`bbss.insecure`** = build-info **field8 (u32)** at **`boot0` offset
   `0x35a98`** on the Classic. Setting it to `1` enables "insecure device;
   ignoring SBL auth failure".
3. **Boot write-protect is *temporary*, not permanent**: `ext_csd[170]
   BOOT_CONFIG_PROT = 0x00`, `ext_csd[173] B_BOOT_WP = 0x04` (only `B_PWR_WP_EN`
   set) — so `boot0` is writable *within* a power-on session **if** `B_PWR_WP_EN`
   can be cleared.
4. **QNX MMC devctl constants** (decoded):
   `DCMD_MMCSD_WRITE_PROTECT = 0xC0201A11`, `DCMD_MMCSD_VUC_CMD = 0xC0441A16`,
   `DCMD_MMCSD_CARD_REGISTER = 0xC0181A14`; encoding
   `(sizeof<<16)+(class<<8)+cmd+0xC0000000` with `_DCMD_CAM=0x0C`, `_SIM_MMCSD=3600`.
5. **The stock MMC driver already contains** the `CMD6 SWITCH ext_csd[173]`
   code path (`WRITE_PROTECT → mmc_switch(0xad)`), but the **raw-command
   passthrough (`VUC_CMD`) is not implemented** (`ENOTTY`) — this is exactly
   what the private `sdmmc.zip` patch adds (per the upstream author).
6. **`/proc/<pid>/as` patching**: `.data`/`.bss` writable, `.text` read-only
   ("Server fault on msg pass"). Cross-process `/proc/<pid>/as` **writes** into
   the trusted driver return `errno 312` (self-writes succeed) — a trust-boundary
   wall, not just a DAC/permission question.
7. **`imggen` + `passport_stage3`** toolchains decoded (public GPL): the
   prototype bootloader, HWI/GPT generation, and the RPM/PBL debug-mode
   (`BOOT_PARTITION_SELECT = 0x5D1`) unlock path.
8. **Oleksandr's raw-MMC interface decoded** (`DCMD_SDMMC_ANY` +
   `sdmmc_raw_cmd`, 44 B, `FUNC_CLEAR_WP = 0x80004`, `cmd_idx` 0–255). It is
   *additive*: the stock driver's dispatch table has no such slot, so it returns
   `ENOTTY`. Re-adding the raw handler is a `.text` patch, which the above
   trust-boundary findings block. (`DCMD_SDMMC_ANY = 0xC02C0E11` by the public
   `_SIM_MMCSD=0x0E10` base; on-device MMC dcmds use a RIM-specific `0x1A..`
   base — see session10a.)
9. **`/dev/mem` on the Passport is a decoy** — opens `O_RDWR` as root yet returns
   a uniform `0xdeadbeef` canary for *every* physical address (full-4GB scan:
   zero ELF headers found), and writes do not persist. No physical-RAM window.
10. **Priv BIDE/Pathtrust** are detection/enforcement LSMs; BIDE never blocks,
   Pathtrust can. Both are defensively written; no unprivileged escalation bug.

---

## Open leads

These are the paths that remain technically open but unverified/unexplored, in
rough order of promise.

1. **Clearing `B_PWR_WP_EN` via the right CMD6 sequence.** The standard
   `WRITE_PROTECT` handler sends `0x03AD0001` (write `ext_csd[173] = 0`) but the
   card returns `SWITCH_ERROR`. Likely requires a vendor/ordering sequence the
   stock handler can't express — e.g. selecting `PARTITION_ACCESS` (`ext_csd[179]`)
   to `boot0` first, or writing `B_PERM_WP_DIS` before `B_PWR_WP_EN`. Needs the
   **raw** command channel (`VUC_CMD` / `DCMD_SDMMC_ANY`), which is missing.
2. **Re-add the raw-command passthrough in the driver** (equivalent of
   Oleksandr's `FUNC_CLEAR_WP`). `.text` is read-only via `/proc/as`, so a direct
   dispatch-table patch is blocked — but the driver's `.data`/`.bss` is **writable**,
   so the live resmgr `dispatch_t` (in heap) or a `.data` function-pointer table
   could route a devctl to a `.data`-resident Thumb thunk that calls the existing
   `mmc_switch` (`0x76c0`) with `ext_csd[173]=0`. Unexplored; the single most
   promising no-desolder lever.
3. **Driver thread hijack** via `/proc/<pid>/ctl` + debug API
   (`DCMD_PROC_STOP` / `SETGREG`) to drive `mmc_switch` directly. Complex,
   unexplored. (Note: `/proc/<pid>/ctl` is *absent* on the Passport, so this is
   Classic-side only, and still needs the debug ability.)
4. **ISP (no-desolder) or desolder** — the hardware route Blanka used. This is
   the known-good fallback and the only confirmed path that defeats the
   boot-partition write-protect.
5. **Priv root via the `kgsl`/QSEE surface** — the community-shared
   `kgsl-exploit` repository may be relevant to the Priv's Android kernel
   (MSM8992), though it is an Android-era driver, not BB10.
6. **Priv `nvuser` token write** — the Priv's unlock token lives in `nvuser`
   (not HW write-protected); reaching the raw partition (ISP or root) would let
   `hlos_unsigned.tkn` be written.

---

## Why doesn't it work? (the honest blockers)

This is the "so what's actually stopping us" summary — the reasons each
half-open door stays shut.

1. **`boot0`/`boot1` are controller-level write-protected.** They return
   `EROFS`/`EIO` even as uid-0. This is `BOOT_WP` re-applied by SBL1 every boot,
   *before* the OS runs, so there is no OS-reachable write window by default.
2. **The MMC driver's raw-command ioctl is absent.** `DCMD_MMCSD_VUC_CMD`
   (`0xC0441A16`) returns `ENOTTY` — BlackBerry stripped the "execute arbitrary
   MMC command" path. Re-adding it means patching `.text`, which is read-only
   via `/proc/as`.
3. **`WRITE_PROTECT` reaches but fails at the switch.** The driver *does* send
   `CMD6 SWITCH ext_csd[173]=0`, but the eMMC rejects it (`SWITCH_ERROR`).
   Clearing a power-on WP flag through the standard path evidently needs a
   sequence (partition select / perm-disable ordering) the stock handler can't
   articulate.
4. **`passport_stage3` (PBL debug mode) is not OS-reachable.** It requires the
   PBL to already be in download/debug (Sahara/EDL-like) mode, which is
   hardware/key gated — same gate as EDL. Not a software path from the running
   OS.
5. **`mmcsdpub` is a publisher, not a toggler.** It only reads `DCMD_MMCSD_DEVINFO`
   and publishes PPS fields; it can't read or clear boot0 write-protect state.
6. **`/dev/mem` is a canary decoy, not physical RAM.** It opens `O_RDWR` as root
   but serves uniform `0xdeadbeef` for every address (and writes don't persist),
   so there is no physical-memory bypass around the `.text` read-only wall.
7. **The raw-command handler must be *added*, not *triggered*.** Oleksandr's
   answer + RE show `DCMD_SDMMC_ANY`/`VUC_CMD` has no dispatch entry in the stock
   driver (`ENOTTY`); no dcmd constant can drive a raw CMD6 on an unpatched
   driver. Re-adding it requires a `.text` write, which is blocked by #6, the
   errno-312 async trust wall, and the immutable `/proc/boot` ramfs.
8. **The Priv's kernel is heavily hardened** (grsecurity/PaX + BIDE + Pathtrust)
   and the shipping `AAW068` source was never released (closest is `AAO474`),
   so weaponizing a Priv kernel bug means finding one blind.

---

## Repository layout

- [`notes/`](notes/) — session-by-session research notes + bug report
- [`analysis/`](analysis/) — sepolicy parsers, disassembly, trustlet JSON
- [`tools/`](tools/) — helper scripts and third-party tool sources
  (`bb10root-tools`, `imggen`, `passport_stage3`)
- [`bootloaders/`](bootloaders/) — prototype (imggen) bootloader images
- [`dumps/`](dumps/) — Classic eMMC dumps + build-info parser
- [`resources/`](resources/) — QNX MMC devctl headers

## References / cited sources

External sources cited across the research. All are publicly accessible; none of
the linked tooling/firmware is re-hosted in this repository (see [LEGAL.md](LEGAL.md)).

| Source | URL | Relevance |
|---|---|---|
| **balika011 — Passport Conversion (BB10 → Android)** | https://balika011.hu/blackberry/guides/passport/conversion.php | The canonical end-to-end unlock: desolder eMMC → `imggen` boot0/user → `ext_csd[179]=0x08` → fastboot → recovery → `adb sideload` LineageOS. Also hosts the LineageOS/recovery images. |
| **bb10.root.sx (Oleksandr)** | https://bb10.root.sx | BB10 root + security notes: RAM-loader `0xF7`/`0xC040` signature-flag mechanics, `install_apk`/`andrB` bar bypass, RCFS/qnx6 sysdata research, real uid-0 via `ota_info_pps.sh` symlink, and the (private) `sdmmc.zip` raw-MMC patch description. |
| **michioxd — skip initial setup in BB QNX** | https://blog.michioxd.ch/blog/02-how-to-completely-skip-initial-setup-in-bbqnx/ | Sachesi + bb10mt + DBBT/cap.exe workflow to unpack/repack a `.signed` QCFM and rebuild an autoloader — the *user/OS* partition modification path (root-and-customize), not a bootloader unlock. |
| **BBAndroids/imggen** | https://github.com/BBAndroids/imggen | Public (GPL-2.0) boot-image generator: `boot_gpt_insecure.bin`/`boot_gpt_secure.bin`, `stage1/2/3.mbn`, `sbl1.mbn`, `aboot.mbn`, `bbss.mbn` — the prototype bootloader + `bbss.insecure` keystone. |
| **BBAndroids/passport_stage3** | https://github.com/BBAndroids/passport_stage3 | "Passport secure boot exploit" — MSM8974AA RPM→PBL debug-mode (`BOOT_PARTITION_SELECT=0x5D1`) path; hardware/key gated from a running OS. |

### Community tooling links (referenced in notes, not re-hosted)

- **Sachesi** — https://github.com/xsacha/Sachesi (extract `.signed` from autoloaders)
- **bb10mt** (BlackBerry 10 MultiTool) — https://bb10.root.sx/downloads/bb10mt/bb10mt.zip
- **cap.exe (FerreiraPablo BlackberrySystemPacker)** — https://github.com/FerreiraPablo/BlackberrySystemPacker
- **QNX Security Whitepaper (Alex Plaskett, MWR)** — https://github.com/alexplaskett/Publications (mwri-qnx-security-whitepaper-2016-03-14.pdf)

## Device connection (SSH)

Connecting to the Classic requires the RSA key **every session** — there is no
password path and no session reuse. See [`notes/session7w-connect-ritual.md`](notes/session7w-connect-ritual.md)
for the required ritual, why `Connection refused` happens, and the quick
reference (`ping` → check port 22 listener → `python3 connect_now.py`).

The private key (`id_rsa`) is a live credential and is gitignored — never
commit it. `connect_now.py` / `reconnect.py` at the repo root document the
paramiko settings (`server_sig_algs=False`, `disable rsa-sha2` pubkeys) needed
to talk to QNX sshd.

## License

Research notes and original scripts are provided as-is for educational
purposes; third-party code retains its own license. See [LEGAL.md](LEGAL.md).
