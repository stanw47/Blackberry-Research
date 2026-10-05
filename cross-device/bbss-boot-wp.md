# Permanent eMMC boot-partition write-protect (`bbss`)

**Applies to:** Classic, Passport (BB10), and the Android BlackBerrys (Priv,
KEYone) via `bbss`/`binfo`. This is the *other* half of the unlock problem.

---

## What it is

BlackBerry's **`bbss`** (build-info / secure-start) sets a **permanent
hardware write-protect** on the eMMC **boot partitions** (`boot0`/`boot1`). Even
as **uid-0 root**, writes to `boot0`/`boot1` return `EROFS`/`EIO`. The bit is
re-applied by the secondary bootloader **every boot**, before the OS runs.

## The bit

```
eMMC EXT_CSD[173] BOOT_WP   = 0x04   -> bit2 B_PERM_WP_EN  (PERMANENT)
eMMC EXT_CSD[174] BOOT_WP_STATUS = 0x0A
```

- `B_PERM_WP_EN` **survives power cycles** and cannot be cleared by the NVRAM
  bits-42/43 ritual (tested: still `0x04` after the cycle).
- The stock MMC driver *does* contain the `CMD6 SWITCH ext_csd[173]` code path,
  but the raw-command passthrough (`VUC_CMD`) is **not implemented** (`ENOTTY`),
  and re-adding it means patching read-only `.text`.

## Android side

On the Android BlackBerrys, `ro.boot.binfo.bbss_wp_type = permanent` and
`bbss_insecure = false`. The same design: the boot partitions are locked by
hardware, and the trust root (`bbss.insecure`) is a build-info field that would
have to be written to `boot0` — which is write-protected.

## How you'd defeat it (all hardware/physical)

1. **Live `CMD6 SWITCH ext_csd[173]=0`** — a `.text`/`.data` driver thunk; blocked
   by the trust boundary (`.text` read-only, cross-process writes errno 312).
2. **ISP / desolder** — the only *confirmed* path (defeats controller WP).
3. **EDL (PBL)** — bypasses the OS and the WP, but needs a signed firehose
   programmer + physical EDL entry. See [edl-firehose.md](edl-firehose.md).

## Evidence

- Classic/Passport: `Blackberry-Classic-Research` / `Blackberry-Passport-Research`
  notes (`boot0` WP decode, `BOOT_WP[173]=0x04`, MMC driver RE).
- KEYone: `ro.boot.binfo.bbss_wp_type=permanent` (live), hub `devmaps/`.
- Priv: `bbss` in the `binfo` boot chain.
