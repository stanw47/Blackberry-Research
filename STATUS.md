# Master Status

> Living status for the whole collection. See [`devices.yml`](devices.yml) for
> the machine-readable index and each device repo's `README.md` for detail.

## Collection at a glance

| Device | Root | Unlock | Custom OS | Headline |
|---|---|---|---|---|
| **Classic** (Q20) | ✅ uid-0 | ⛔ HW-gated | 🔬 A11-on-QNX port | `pathtrust !__root` real root |
| **Passport** | ✅ uid-0 | 🔬 power-on WP | 🔬 user-area boot | live `ext_csd`: WP not fused; wipe ritual |
| **Passport (proto)** | ✅ vold-domain | ⛔ authboot | — | Dirty COW → vold root; boot chain dumped |
| **Q10** (proto) | — | ? | — | device incoming |
| **Priv** | ⛔ | ⛔ | ⛔ | authboot/RTAS decoded |
| **KEYone** | ⛔ | ⛔ | ⛔ | reachable KGSL/IOMMU kernel bug |
| **KEY2** | ✅ | ✅ | ✅ LineageOS 22.2 | CVE-2021-1931 unlock |
| **Bold 9930** | ⛔ | — | — | RRT signing boundary mapped |

Legend: ✅ done · ⛔ blocked · 🔬 research · ? unknown

## Per-device status (one line each)

- **Classic** — rooted (uid-0), bootable, recoverable; unlock blocked by
  permanent boot-partition write-protect; A11-on-QNX port in progress
  (bionic shim runs; binder + A11 userland are the frontier).
- **Passport** — current (replacement) board **rooted (uid-0)**, bootable and
  reflashable; live `ext_csd` shows the boot-partition WP is **power-on
  (`B_PWR_WP_EN`), not fused**; no-desolder `imggen` path mapped; the
  user-area-boot experiment is the open lane. Old board parked in `11011`
  (`FS_DIRTY_ALL` RPMB-backed).
- **Passport (Android prototype, `oslo`)** — alive; rooted in the `vold` domain
  via Dirty COW + a patched `fsck_msdos` (non-persistent); boot/recovery/modem,
  boot chain, kernel/ramdisk dumped; no autoloader exists — read-only specimen.
- **Q10** — prototype unit incoming; repo scaffolded.
- **Priv** — not rooted; `authboot`/RTAS2 + ECDSA boot gate fully decoded;
  Widevine-trustlet underflow analyzed; no public kernel 0-day.
- **KEYone** — locked; no software unlock; reachable KGSL/IOMMU bug
  (CVE-2020-11261 / CVE-2023-33107 class) from unprivileged `shell` (DoS).
- **KEY2** — **unlocked** via CVE-2021-1931 (`kibo`); running LineageOS 22.2.
- **Bold 9930** — recon + RRT code-signing boundary mapped; BootROM lane in progress.

## Cross-device conclusions (pinned)

1. **authboot/RTAS2** makes software unlock impossible on locked Android
   BlackBerrys. → [cross-device/authboot-rtas.md](cross-device/authboot-rtas.md)
2. **Power-on eMMC boot WP** (`B_PWR_WP_EN`, re-applied by the boot chain every
   boot — *not* a fused `B_PERM_WP_EN`; live `ext_csd` reads on Classic + retail
   Passport) blocks boot-partition writes as root when combined with the missing
   CMD6 path. → [cross-device/bbss-boot-wp.md](cross-device/bbss-boot-wp.md)
3. **EDL** is the universal bypass, gated by physical entry + a signed firehose
   programmer. → [cross-device/edl-firehose.md](cross-device/edl-firehose.md)
4. **Legacy LK vs modern UEFI ABL** explains KEY2 unlock vs Priv/KEYone block.
   → [cross-device/lk-vs-abl.md](cross-device/lk-vs-abl.md)
5. **BB10 real root** is software-only via `pathtrust !__root`.
   → [cross-device/bb10-root-pathtrust.md](cross-device/bb10-root-pathtrust.md)
6. **QNX `vtnvfs`/`/nvram`** token storage is present on BB10 *and* Android
   BlackBerrys, with the token-write paths gated on shipped units.
   → [cross-device/qnx-vtnvfs.md](cross-device/qnx-vtnvfs.md)

## Changelog (major updates)

- **2026-10-08** — Passport: live `ext_csd` read (**boot WP is power-on, not
  fused**); exact `LDR_77` RAM-loader bring-up; an interrupted BootROM handshake
  arms the by-design security wipe (3-button reset + autoloader reflash ritual
  documented); uid-0 restored; user-area-boot experiment spec + a working
  cross-built QNX userland toolchain (`extcsd_probe`). Three-way component diff
  (stock BB10 / Balika kit / prototype Android): kit `stage1`/`stage2` are
  byte-identical to the prototype's secure `bbss`/`sbl1r`; **`stage3` payload
  exploit decoded** (PBL debug mode → skips SBL auth, loads the GPT `bbss`
  partition) and tracked; candidate insecure boot image assembled.
- **2026-10-05** — Multi-repo restructure completed. Hub slimmed to a minimal
  index; per-device repos (Classic, Passport, Priv, Q10) created and populated;
  KeyOne/Key2 split by device; all session notes and non-note artifacts
  distributed to their device repos; meta/planning docs kept out of all repos.
- **2026-10-04** — Classic network audit: rooted autoloader + a re-signed
  Telegram APK cleared of a "phone-home" claim.
- **2026-10-03** — KEYone: KGSL/IOMMU kernel bug confirmed reachable from shell.
- **2026-10-02** — KEYone/Priv authboot decode; KEYone autoloader teardown
  (signed MSM8953 firehose programmer extracted).
- **2026-09** — KEY2 unlocked + LineageOS; Classic real root; Passport driver
  forensics.

## Next

- Map the incoming **Q10 prototype** (L0→L1) and add its devmap.
- Flip device repos **public** as each write-up is finalized.
- Populate `devmaps/` for Priv and 9930.
- Add a `toolchain/sync-hub.sh` to aggregate each repo's `SUMMARY.md`.
