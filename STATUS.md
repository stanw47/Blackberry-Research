# Master Status

> Living status for the whole collection. See [`devices.yml`](devices.yml) for
> the machine-readable index and each device repo's `README.md` for detail.

## Collection at a glance

| Device | Root | Unlock | Custom OS | Headline |
|---|---|---|---|---|
| **Classic** (Q20) | ✅ uid-0 | ⛔ HW-gated | 🔬 A11-on-QNX port | `pathtrust !__root` real root |
| **Passport** | ✅ (bricked) | ⛔ HW-gated | 🔬 imggen path | `imggen` no-desolder path mapped |
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
- **Passport** — rooted but **red-blink / non-bootable**; `FS_DIRTY_ALL` is
  RPMB-backed; the no-desolder `imggen` Android path is mapped; recovery is the
  open task.
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
2. **Permanent eMMC boot WP** (`B_PERM_WP_EN`) blocks boot-partition writes even
   as root. → [cross-device/bbss-boot-wp.md](cross-device/bbss-boot-wp.md)
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
