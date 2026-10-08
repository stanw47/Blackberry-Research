# eMMC boot-partition write-protect (`bbss` / `BOOT_WP`)

**Applies to:** Classic, Passport (BB10), and the Android BlackBerrys (Priv,
KEYone) via `bbss`/`binfo`. This is the *other* half of the unlock problem.

---

## What it is

BlackBerry's **`bbss`** (build-info / secure-start) manages the eMMC
**boot-partition write-protect** (`boot0`/`boot1`) and re-applies it **every
boot**, before the OS runs. From a running OS, writes to `boot0`/`boot1` return
`EROFS`/`EIO`, even as **uid-0 root**.

## The bits (corrected 2026-10-08)

```
eMMC EXT_CSD[170] BOOT_CONFIG_PROT = 0x00   -> boot config NOT fused
eMMC EXT_CSD[173] BOOT_WP          = 0x04   -> bit2 B_PWR_WP_EN (POWER-ON WP)
eMMC EXT_CSD[174] BOOT_WP_STATUS   = 0x0A
```

- The earlier "permanent (`B_PERM_WP_EN`)" reading of `0x04` was a bit-numbering
  error: bit0 is `B_PERM_WP_EN`, **bit2 is `B_PWR_WP_EN`**. Live `ext_csd` reads
  on the **Classic** (2026-08-30) and the **retail Passport** (2026-10-08) both
  show `[170] = 0x00`, `[173] = 0x04` → **power-on, not fused**.
- It still *behaves* like a wall: the boot chain re-applies it at every boot, the
  stock MMC driver's `WRITE_PROTECT` clear returns `EIO` and changes nothing
  (verified live on the Passport), and the raw-command passthrough (`VUC_CMD`)
  is not implemented (`ENOTTY`).
- Consequence: the clear must come from a context that runs **before** the boot
  chain re-applies it (RAM-loader / official updater) or from hardware.

## Android side

On the Android BlackBerrys, `ro.boot.binfo.bbss_wp_type = power-on | permanent`
(the Android Passport prototype reports `power-on`) and `bbss_insecure = false`.
Same design: the boot partitions are locked by the boot chain, and the trust
root (`bbss.insecure`) is a build-info field stored in `boot0` — which is
protected.

## How you'd defeat it

1. **CMD6 `SWITCH ext_csd[173]` from a loader/updater context** — the
   factory/RAM-loader path runs before the chain re-applies the WP; the official
   updater is the intended no-solder lane (see the Passport `session29`
   user-area-boot experiment).
2. **ISP / desolder** — the only *confirmed* path (defeats controller WP).
3. **EDL (PBL)** — bypasses the OS and the WP, but needs a signed firehose
   programmer + physical EDL entry. See [edl-firehose.md](edl-firehose.md).
4. **OS-driver `.data` thunks / raw-MMC re-add** — blocked in practice on the
   Passport by the cross-process `/proc/<pid>/as` trust boundary
   (writes → `errno 312`); `.text` is read-only.

## Evidence

- Classic/Passport: `Blackberry-Classic-Research` / `Blackberry-Passport-Research`
  notes — live `ext_csd` (`BOOT_CONFIG_PROT=0x00`, `BOOT_WP=0x04`), MMC driver
  RE, and the Passport `session29` `extcsd_probe` tool.
- Prototype: `ro.boot.binfo.bbss_wp_type=power-on`.
- KEYone: `ro.boot.binfo.bbss_wp_type=permanent` (live), hub `devmaps/`.
- Priv: `bbss` in the `binfo` boot chain.
