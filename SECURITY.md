# Safety / Disclaimer

This is a **research aid**, not a flashing guide. Before you do anything in
this repository, understand the following.

## You can permanently destroy your device

Actions documented or implied here — writing to `boot0`/`boot1`, clearing the
eMMC boot write-protect (`B_PWR_WP_EN` in `ext_csd[173]`), toggling
`bbss.insecure`, or reflashing the bootloader — can make a device **permanently
unbootable**. Recovery typically requires desoldering the eMMC and reflashing it
externally (chip-off / JTAG / ISP programmer). This is not a "soft brick."

## There is no undo button

The boot ROM / secondary bootloader signature and security-state flags are
one-way or near-one-way. Once you write a bad bootloader or an invalid value to
a security field, a normal reboot will not recover it.

## Back up first

The research workflow relied on dumping `boot0`, `boot1`, `nvram0`, and `dmi0`
before any modification. If you do not have verified, byte-identical backups of
your device's boot partitions, **do not proceed**.

## Exclusive access / unmounting

Issuing raw eMMC commands while a filesystem is mounted can corrupt the mounted
filesystem. The notes describe cases where filesystems/pages are cached, leading
to "same block read repeatedly" artifacts. Always unmount relevant volumes and
use exclusive access before raw access.

## Legal

See [LEGAL.md](LEGAL.md). Unlocking a bootloader may void warranty and may
violate terms of service. Only perform research on devices you own and are
authorized to test.

## No warranty

THE MATERIALS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. THE AUTHOR
DISCLAIMS ALL LIABILITY FOR DAMAGE, DATA LOSS, BRICKED DEVICES, OR LEGAL
CONSEQUENCES ARISING FROM USE OF THIS MATERIAL.
