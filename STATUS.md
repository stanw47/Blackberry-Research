# Master Status

> Living status for the whole collection. Updated as devices are added and
> results land. See [`devices.yml`](devices.yml) for the machine-readable index.

## Collection at a glance

| Device | Root | Unlock | Custom OS | Headline |
|---|---|---|---|---|
| Classic (Q20) | ✅ uid-0 | ⛔ HW-gated | 🔬 A11-on-QNX port | pathtrust `!__root` real root |
| Passport | ✅ (bricked) | ⛔ HW-gated | 🔬 imggen path | `imggen` no-desolder path mapped |
| Q10 (proto) | — | ? | — | device incoming |
| Priv | ⛔ | ⛔ | ⛔ | authboot/RTAS decoded |
| KEYone | ⛔ | ⛔ | ⛔ | reachable KGSL/IOMMU kernel bug |
| KEY2 | ✅ | ✅ | ✅ LineageOS 22.2 | CVE-2021-1931 unlock |
| Bold 9930 | ⛔ | — | — | RRT signing boundary mapped |

Legend: ✅ done · ⛔ blocked · 🔬 research · ? unknown

## Cross-device conclusions (pinned)

1. **authboot/RTAS** makes software unlock impossible on locked Android
   BlackBerrys. → [cross-device/authboot-rtas.md](cross-device/authboot-rtas.md)
2. **Permanent eMMC boot WP** (`B_PERM_WP_EN`) blocks boot-partition writes even
   as root. → [cross-device/bbss-boot-wp.md](cross-device/bbss-boot-wp.md)
3. **EDL** is the universal bypass, gated by physical entry + a signed firehose
   programmer. → [cross-device/edl-firehose.md](cross-device/edl-firehose.md)
4. **Legacy LK vs modern ABL** explains KEY2 unlock vs Priv/KEYone block.
   → [cross-device/lk-vs-abl.md](cross-device/lk-vs-abl.md)
5. **BB10 real root** is software-only via `pathtrust !__root`.
   → [cross-device/bb10-root-pathtrust.md](cross-device/bb10-root-pathtrust.md)

## Changelog (major updates)

- **2026-10-05** — Multi-repo split begun. Hub + per-device repos
  (Classic, Passport, Priv, Q10) scaffolded to the new standard; KEY2/KEYone/9930
  already existed. Standards + templates added (`docs/STANDARDS.md`).
- **2026-10-04** — Classic network audit: rooted autoloader + a re-signed
  Telegram APK cleared of the "phone-home" claim (see Classic repo `recon/`).
- **2026-10-03** — KEYone: KGSL/IOMMU kernel bug confirmed reachable from shell.
- **2026-10-02** — KEYone/Priv authboot decode; KEYone autoloader teardown
  (firehose programmer extracted).
- **2026-09** — KEY2 unlocked + LineageOS; Classic real root; Passport driver
  forensics.

## Next

- Map the incoming **Q10 prototype** (L0→L1) and add its devmap.
- Flip device repos **public** as each write-up is finalized.
- Populate `devmaps/` for Priv and 9930.
- Add a `toolchain/sync-hub.sh` to aggregate each repo's `SUMMARY.md`.
