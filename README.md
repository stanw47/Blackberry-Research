# BlackBerry Research

Reverse-engineering notes, artifacts, and tooling for **BlackBerry 10 (BB10/QNX)**
and **BlackBerry Android** devices — including the bootloader-unlock / Android
port effort for the **Classic** (MSM8960) and **Passport** (MSM8974).

> **Disclaimer — read first.** This repo is a *research aid*, not a flashing
> guide. Nothing here is production code or an endorsed procedure. Flashing,
> editing eMMC boot partitions (`boot0`/`boot1`), toggling `BOOT_WP`/`bbss.insecure`,
> or writing `ext_csd` can **permanently brick** a device with no recovery short
> of JTAG/ISP chip-out. Everything is at your own risk, for educational /
> defensive research on devices you own. Third-party firmware/bootloaders
> appear only where needed to document findings; see [LEGAL.md](LEGAL.md).

---

## Contents

1. [Devices](#devices)
2. [Status summary](#status-summary)
3. [What was attempted](#what-was-attempted)
4. [Key findings](#key-findings)
5. [Open leads](#open-leads)
6. [Why each blocker holds](#why-each-blocker-holds)
7. [Repository layout](#repository-layout)
8. [References](#references)
9. [Device connection (SSH)](#device-connection-ssh)
10. [License](#license)

---

## Devices

| Device | OS | SoC | Build / variant |
|---|---|---|---|
| **Classic** | BB10 / QNX | MSM8960 | `QNX BLACKBERRY-528E`, CLASSICNA |
| **Passport** | BB10 / QNX | MSM8974AA | `QNX BLACKBERRY-603C`, WINDERMEREEMEA |
| **Priv** | Android | MSM8992 | `AAW068`, venicena |

---

## Status summary

| Device | Status |
|---|---|
| **Classic** | Fully rooted (real uid-0), running 10.3.3.3216, recoverable via Windows `cap.exe` autoloader. Unlock understood but HW-gated. |
| **Passport** | Fully rooted (real uid-0). Driver forensics complete. Currently **red-blink / non-bootable** after a reboot (see [current device state](#current-device-state)). |
| **Priv** | Not rooted. Needs a kernel 0-day (none public) or ISP access. |

**The unlock goal** (Classic + Passport): write one byte — `bbss.insecure`
(build-info field8, `boot0` offset `0x35a98`). That byte is **hardware write-
protected** (`BOOT_WP[173]=0x04`, bit2 `B_PERM_WP_EN`, *permanent*), which is
the core problem this repo attacks.

**The Android goal** (Passport): `imggen` payloads are built and validated
offline (`boot0.img` / `new_user.img`); they are not flashed yet. See
[#16](#key-findings) and the [AUTOLOADER_GUIDE](docs/AUTOLOADER_GUIDE.md).

### Current device state

- **Classic:** bootable, rooted, recoverable.
- **Passport:** after session19's driver-forensics reads (no writes) the device
  was rebooted and entered a **red-blink loop** (the documented stub/payload
  recovery-path issue, finding #12). Attempted stock + pre-rooted autoloader
  recovery from Windows now **fails at the "Signature Trailer" step (~13%)**;
  the device currently blinks `11011` and will not return to BootROM. Recovery
  options under investigation: EDL lane (`tools/listen_flash.py --armed`,
  listener-first), or the hardware/ISP route. See
  [`notes/session19-driver-gate-decode-and-passport-dumps.md`](notes/session19-driver-gate-decode-and-passport-dumps.md).

> **Boot0 write-protect status (2026-09-09).** `BOOT_WP[173] = 0x04`
> (bit2 `B_PERM_WP_EN`, *permanent*), re-applied every boot. The rimboot
> software lane is **closed** (sessions 16–18): the WP gate aborts first; a
> NOP-bypass fails `EROFS` at the driver; the NVRAM-arming power-cycle ritual
> leaves it `0x04`. Remaining paths: a live-driver raw `cmd6 SWITCH
> ext_csd[173]=0` thunk (blocked by the `/proc/as` ability regression), or the
> hardware/EDL lane.

---

## What was attempted

### BB10 / QNX (Classic + Passport)

1. **Root via `bb10.root.sx` getroot payload** — succeeded (pre-rooted autoloader,
   `btool` runs as root at boot via an `ota_info_pps.sh` symlink).
2. **Real interactive uid-0** — added `/proc/boot/pathtrust !/base/bin/__root`
   to `btool`; `__root` becomes path-trust-trusted every boot.
3. **Raw eMMC read without desoldering** — the setgid group wrapper
   `g_Disk_Drivers` grants the `Disk_Drivers` group (read/write to `/dev/emmc/*`).
4. **eMMC dumps** — `boot0`, `boot1`, `nvram0`, `dmi0` recovered to `dumps/`.
5. **`bbss.insecure` pinning** — build-info field8 (u32) at `boot0` offset
   `0x35a98` (currently `0` = secure), decoded from the public `imggen` toolchain.
6. **Bootloader write attempt** — blocked. `boot0`/`boot1` are HW write-protected
   (`EROFS` even as root); `uda0`/`os0`/`dmi0` are writable.
7. **QNX MMC devctl RE** — decoded `DCMD_MMCSD_WRITE_PROTECT` (`0xC0201A11`),
   `DCMD_MMCSD_VUC_CMD` (`0xC0441A16`), `DCMD_MMCSD_CARD_REGISTER` (`0xC0181A14`)
   and the internal dispatch table of `sdmmc-rim-msmsdcc`.
8. **Live CMD6 SWITCH / WP-toggle attempts** — `WRITE_PROTECT` returns `EIO`;
   `VUC_CMD` returns `ENOTTY` (not implemented).
9. **`/proc/<pid>/as` memory patching** — `.data`/`.bss` writable, `.text`
   read-only ("Server fault on msg pass"); cross-process writes return errno 312.
10. **`/dev/mem` audit (Passport)** — ruled out: opens `O_RDWR` but serves a
    uniform `0xdeadbeef` canary, no persistence (session10a).

### Priv (Android)

1. **Kernel source audit** — mapped the in-kernel security stack
   (grsecurity/PaX, BIDE, Pathtrust) from the GPL source.
2. **BIDE / Pathtrust audit** — no unprivileged escalation primitive found.
3. **QSEE / trustlet surface audit** — enumerated SELinux domains and audited
   `vend_fidodaemon` / token-service.
4. **Reported bug** — a genuine `fget()`-without-`fput()` ref leak in
   `security/pathtrust/ioctl.c` ([notes/bug-report-pathtrust-fput-leak.md](notes/bug-report-pathtrust-fput-leak.md)).

---

## Key findings

*Durable, pinned facts, cross-referenced in [`notes/`](notes/). Numbering is
stable; new findings append.*

### Root, unlock, and the boot0 wall

1. **Real uid-0** on BB10 via the path-trust whitelist trick
   (`/proc/boot/pathtrust !/base/bin/__root`).
2. **`bbss.insecure`** = build-info field8 (u32) at `boot0` offset `0x35a98`
   (Classic). Setting it to `1` enables "insecure device; ignoring SBL auth
   failure".
3. **Boot write-protect is *permanent*** (Passport, live re-read):
   `BOOT_WP[173] = 0x04` = bit2 `B_PERM_WP_EN`; `BOOT_WP_STATUS[174] = 0x0A`.
   The NVRAM bits-42/43 power-cycle ritual does **not** clear it (session18).
   Only a live `CMD6 ext_csd[173]=0` (software thunk) or the hardware/EDL lane
   can get a boot0 write.
4. **QNX MMC devctl constants:** `WRITE_PROTECT=0xC0201A11`,
   `VUC_CMD=0xC0441A16`, `CARD_REGISTER=0xC0181A14`; encoding
   `(sizeof<<16)+(class<<8)+cmd+0xC0000000` (`_DCMD_CAM=0x0C`, `_SIM_MMCSD=3600`).
5. **The stock MMC driver already contains** the `CMD6 SWITCH ext_csd[173]`
   code path (`WRITE_PROTECT → mmc_switch(0xad)`), but the raw-command
   passthrough (`VUC_CMD`) is **not implemented** (`ENOTTY`).
6. **`/proc/<pid>/as` patching:** `.data`/`.bss` writable, `.text` read-only;
   cross-process writes to a trusted driver return errno 312 (trust-boundary wall).
7. **`imggen` + `passport_stage3`** (public GPL) decoded: prototype bootloader,
   HWI/GPT generation, and the RPM/PBL debug-mode (`BOOT_PARTITION_SELECT=0x5D1`)
   unlock path.
8. **Oleksandr's raw-MMC interface decoded** (`DCMD_SDMMC_ANY` + `sdmmc_raw_cmd`,
   44 B, `FUNC_CLEAR_WP=0x80004`, `cmd_idx` 0–255). It is *additive*; the stock
   driver has no such slot → `ENOTTY`. Re-adding it is a `.text` patch, blocked
   by the trust-boundary findings.
9. **`/dev/mem` on the Passport is a decoy** — uniform `0xdeadbeef`, no
   persistence, no physical-RAM window.
10. **Priv BIDE/Pathtrust** are detection/enforcement LSMs; defensively written,
    no unprivileged escalation bug.

### The install seal and the red-blink

11. **The 560-byte install-seal contract.** The RAM-loader's `F9 40`
    (SIGNATURE_TRAILER) is what SBL validates to accept an OS install. bb10mt
    only strips+sends a carrier's last 560 bytes if they begin with `QNXH`; the
    OS carrier ends in 560 zero bytes, so bb10mt streams zeros + sends a fake
    seal. `cap.exe` embeds the real 560-byte seal as a PEM `SIGNATURE BLOCK`
    (decodes to `0xFF` EMSA-PKCS#1 padding + RSA records + `1F2DC8D7` footer).
12. **Red-blink root cause is the stub, not the payload.** Byte-identical
    OS/radio carriers: bb10mt → red-blink; Windows `cap.exe` → boots. Even the
    real 560-byte block via bb10mt red-blinks — cap.exe does more flash-time
    state than just `F9`. Capturing cap.exe-vs-bb10mt USB traffic is the
    highest-value experiment.
13. **Classic is MSM8960 (SBL2→SBL1); imggen is MSM8974-only.** Classic
    `boot0.img` GPT = `SBL2`+`SBL1`; imggen hwids are all `0x2c` (Passport/oslo);
    Classic is `0x27`. Bundled MSM8974 loaders can't boot MSM8960. No Classic
    Android via imggen.
14. **NVRAM unlock flags** (bits 42/43 ⇒ byte5 `0x0C` in NV record `0x2019`)
    persist across reboot. They gate the **official updater's boot0-write path**,
    not the running OS block layer (`pwrite /dev/emmc/boot0` stays `EROFS`).
15. **Device flash entry is listener-first.** Powered-off+plugged only charges;
    the device enters BootROM (`0x0001`) → RAM-loader (`0x8001`) only when a
    host tool is already polling VID `0x0FCA`. A live OS device enumerates as
    PID `0x8017`; loader sessions start with the device OFF.

### Passport driver forensics (session19)

16. **Passport no-desolder conversion is the viable Android path.** MSM8974 =
    imggen's exact target; we have the rooted Passport autoloader, the
    `8D002C0A` RAM-loader lane, proven OS-side eMMC dumps, and the persisted
    NV unlock. Remaining gate = read-only loader session to map the Boot0
    region, then the loader's raw boot-region write op.
17. **The rimboot (`rimboot_update`) software lane is closed** (sessions 16–18):
    own gate aborts `rc=1`; NOP-bypass fails `EROFS` (original bootrom intact);
    forced `r0==1` branch arms NV bits + clean shutdown, yet post-cycle
    `BOOT_WP[173]` is still `0x04`.
18. **MMC driver gate `0xF182` and WP handler `0x108D0` fully decoded.** Gate:
    `[ext+4].bit0==1` and `[ext + idx + 0x1f8] != 0`, where
    `idx = msg[0xa]*0x2c8 + msg[0xb]*0x58`. Handler computes `idx`, calls gate,
    requires `[ext+0x24]==1`, then calls the `mmc_switch` worker with the
    mode-table byte (`0->0x1d, 1(BOOT_WP)->0x1c, 2->0x1e, 3->0x1f`).
19. **`ext` is per-open-node, not global.** Identical `WRITE_PROTECT` probes on
    `/dev/emmc/user0` (rc=0) and `/dev/emmc/boot1` (rc=5/EIO) use the same
    payload (`lba=0 → idx=0`) yet diverge — the difference is the `ext=[ctx+8]`
    per-open context. User0's ext has `[ext+4].bit0=1` and `[ext+0x1f8]!=0`;
    boot1's lacks one or both.
20. **CID is live-read, not cached.** All three partitions return the same CID
    `00 91 b2 63 55 93 00 34 45 47 32 33 30 00 01 11`; zero 16-byte hits in all
    writable RAM dumps.
21. **No 512-byte ext_csd cache anywhere.** Exact-signature + anchor scan
    (`[0xAA]=00, [0xAD]=04, [0xAE]=0A`) across heap, module data, and all anon
    spans → 0 hits.
22. **Passport `boot0` holds SBL1 (1 MiB); `boot1` is blank.** EFI PART at
    `0x200` is a minimal decoy (single "BootROM" entry, LBA 34–511); SBL1
    strings + 3 ELF magics confirmed. `os0` holds the QNX IFS. Dumps in
    `dumps/passport/`.

---

## Open leads

*Technically open but unverified, roughly in promise order.*

1. **Raw `cmd6 SWITCH ext_csd[173]=0` thunk** — the driver's `.data`/`.bss` is
   writable, so a resmgr `dispatch_t` or `.data` function-pointer table could
   route a devctl to a `.data`-resident Thumb thunk calling the existing
   `mmc_switch` (`0x76c0`). **Session19 caveat:** `ext` is per-open-node, so a
   global patch must target the `ext` used by the boot1 open context (or patch
   the open routine to set `[ext+4].bit0` / `[ext+0x1f8]` at allocation).
   The single most promising no-desolder lever.
2. **Driver thread hijack** via `/proc/<pid>/ctl` + debug API
   (`DCMD_PROC_STOP`/`SETGREG`) to drive `mmc_switch`. Absent on the Passport
   (Classic-side only), still needs the debug ability.
3. **ISP (no-desolder) or desolder** — the only *confirmed* path that defeats
   the boot-partition WP.
4. **Priv: `kgsl`/QSEE surface** — community `kgsl-exploit` may map to the
   MSM8992 kernel.
5. **Priv `nvuser` token write** — `hlos_unsigned.tkn` lives in `nvuser`
   (not HW WP); reaching the raw partition (ISP or root) enables it.
6. **Raw EDL boot-partition writer** — `bblink.py` implements `F7/F8`, `EE`,
   `cread`, `preflash`, `complete`, `reboot` + MCT save. Remaining work: map the
   live Boot0 MCT entry (kind `$2B`) read-only, craft the boot0-targeted write.
   Wiped units can trigger a security wipe → listener-first on a *live* device.
7. **Capture cap.exe-vs-bb10mt USB delta** — pin the stub's injection so custom
   images can flash on the same lane.

---

## Why each blocker holds

1. **`boot0`/`boot1` are controller-level WP.** `EROFS`/`EIO` even as uid-0;
   WP re-applied by SBL1 each boot before the OS runs.
2. **The MMC driver's raw-command ioctl is absent.** `VUC_CMD` → `ENOTTY`;
   re-adding it means patching `.text`, which is read-only via `/proc/as`.
3. **`WRITE_PROTECT` reaches but fails at the switch.** The card rejects
   `CMD6 SWITCH ext_csd[173]=0`; the bit is `B_PERM_WP_EN` (permanent), and the
   power-cycle ritual doesn't clear it.
4. **`passport_stage3` (PBL debug mode) is not OS-reachable** — needs PBL in
   Sahara/EDL-like mode, hardware/key gated.
5. **`mmcsdpub` is a publisher, not a toggler.** Reads `DCMD_MMCSD_DEVINFO`,
   publishes PPS fields; can't touch boot WP state.
6. **`/dev/mem` is a canary decoy.** No physical-memory window around the
   `.text` read-only wall.
7. **The raw-command handler must be *added*, not *triggered*.** No dcmd drives
   a raw CMD6 on the unpatched driver; re-adding is a `.text` write blocked by
   errno-312 + immutable `/proc/boot`.
8. **The Priv's kernel is heavily hardened.** grsecurity/PaX + BIDE + Pathtrust;
   shipping `AAW068` source never released (closest `AAO474`) — finding a bug =
   blind.

---

## Repository layout

- [`notes/`](notes/) — session-by-session research notes + bug report
- [`analysis/`](analysis/) — sepolicy parsers, disassembly, trustlet JSON
- [`tools/`](tools/) — helper scripts + third-party tool sources
  (`bb10root-tools`, `imggen`, `passport_stage3`, `bblink.py`,
  `listen_flash.py`, `classic_repack.py`, …)
- [`bootloaders/`](bootloaders/) — prototype (imggen) bootloader images
- [`dumps/`](dumps/) — Classic eMMC dumps + build-info parser
- [`dumps/passport/`](dumps/passport/) — Passport eMMC dumps (SBL1, boot1, os0 IFS)
- [`resources/`](resources/) — QNX MMC devctl headers
- [`docs/`](docs/) — cross-device analysis, device/connection reference,
  [AUTOLOADER_GUIDE.md](docs/AUTOLOADER_GUIDE.md)

---

## References

All public and not re-hosted here (see [LEGAL.md](LEGAL.md)).

| Source | URL | Relevance |
|---|---|---|
| **balika011 — Passport conversion** | https://balika011.hu/blackberry/guides/passport/conversion.php | Canonical end-to-end unlock: desolder eMMC → `imggen` boot0/user → `ext_csd[179]=0x08` → fastboot → recovery → `adb sideload` LineageOS. Under active reproduction no-desolder via the RAM-loader lane. |
| **bb10.root.sx (Oleksandr)** | https://bb10.root.sx | BB10 root + security notes: RAM-loader `0xF7`/`0xC040` signature-flag mechanics, RCFS/qnx6 sysdata research, real uid-0, and the private `sdmmc.zip` raw-MMC patch. |
| **michioxd — skip initial setup** | https://blog.michioxd.ch/blog/02-how-to-completely-skip-initial-setup-in-bbqnx/ | Sachesi + bb10mt + DBBT/cap.exe workflow to unpack/repack `.signed` QCFM + rebuild an autoloader (user/OS partition path). |
| **BBAndroids/imggen** | https://github.com/BBAndroids/imggen | Public (GPL-2.0) boot-image generator: prototype bootloader + `bbss.insecure` keystone. |
| **BBAndroids/passport_stage3** | https://github.com/BBAndroids/passport_stage3 | "Passport secure boot exploit" — MSM8974AA RPM→PBL debug-mode (`BOOT_PARTITION_SELECT=0x5D1`) path. |

**Community tooling:** [Sachesi](https://github.com/xsacha/Sachesi) ·
[bb10mt](https://bb10.root.sx/downloads/bb10mt/bb10mt.zip) ·
[cap.exe / BlackberrySystemPacker](https://github.com/FerreiraPablo/BlackberrySystemPacker) ·
[QNX Security Whitepaper (MWR)](https://github.com/alexplaskett/Publications)

---

## Device connection (SSH)

Connecting requires the RSA key **every session**. See
[`docs/ssh-connection-linux.md`](docs/ssh-connection-linux.md) for the full
Linux guide (Dev Mode, fresh keygen, `blackberry-connect` tunnel, paramiko with
QNX algorithm fixes) and [`notes/session7w-connect-ritual.md`](notes/session7w-connect-ritual.md).

The private key (`id_rsa`) is gitignored — never commit it.

---

## License

Research notes and original scripts are available for educational purposes;
third-party code retains its own license. See [LEGAL.md](LEGAL.md).