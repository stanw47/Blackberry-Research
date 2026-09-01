# BlackBerry Research

Security research notes, reverse-engineering artifacts, and tooling for the
BlackBerry 10 (BB10/QNX) and BlackBerry Android-era devices.

> **⚠️ DISCLAIMER — READ THIS FIRST**
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

## Contents

- [`notes/`](notes/) — session-by-session research notes (root, eMMC, driver RE)
- [`analysis/`](analysis/) — decoded artifacts (sepolicy parsers, disassembly,
  trustlet JSON, eMMC dump descriptions)
- [`tools/`](tools/) — helper scripts and third-party tool sources
- [`bootloaders/`](bootloaders/) — small firmware images referenced by the notes
- [`resources/`](resources/) — QNX MMC devctl headers and reference material

## Summary of findings

1. **Real uid-0 root on BB10 Classic and Passport** via a path-trust whitelist
   trick in `btool` (`/proc/boot/pathtrust !/base/bin/__root`).
2. **Boot-partition write-protect is power-on temporary, not permanent** —
   `ext_csd[170] BOOT_CONFIG_PROT = 0x00`, `ext_csd[173] B_BOOT_WP = 0x04`
   (only `B_PWR_WP_EN` set).
3. The `bbss.insecure` flag lives at `boot0` offset `0x35a98` (Classic).
4. The QNX MMC devctl interface was decoded (`DCMD_MMCSD_WRITE_PROTECT =
   0xC0201A11`, `DCMD_MMCSD_VUC_CMD = 0xC0441A16`, etc.), and the stock driver
   (`sdmmc-rim-msmsdcc`) was reverse-engineered: its `WRITE_PROTECT` handler
   already contains the `CMD6 SWITCH ext_csd[173]` code path, but the stock
   driver returns `ENOTTY` for the raw-command passthrough that would be needed
   to send an arbitrary vendor sequence.

See [`notes/`](notes/) for full detail.

## Devices

- **Classic** — QNX BLACKBERRY-528E, MSM8960, CLASSICNA
- **Passport** — QNX BLACKBERRY-603C, MSM8974AA, WINDERMEREEMEA
- **Priv** — Android AAW068, MSM8992, venicena

## License

Research notes and original scripts in this repository are provided as-is for
educational purposes. Third-party code retains its own license (see individual
files / [`LEGAL.md`](LEGAL.md)).
