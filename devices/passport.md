# Passport (SQW100)

| Field | Value |
|---|---|
| SoC | MSM8974AA |
| OS | BB10 / QNX — old board `BLACKBERRY-603C`; current board `BLACKBERRY-E538` |
| Bootloader | locked; boot-partition WP **power-on (`B_PWR_WP_EN`), not fused** — live `ext_csd` (2026-10-08) |
| Root | rooted (uid-0) on the current board; old board red-blink `11011` |
| Repo | https://github.com/stanw47/Blackberry-Passport-Research (private) |

**Headline:** MSM8974AA = exact `imggen` target → no-desolder Android/unlock path
mapped; live `ext_csd` corrected the WP model (power-on, not permanent); the
user-area-boot experiment is the open software lane.

**Status:** current unit bootable + rooted; RAM-loader bring-up reached BootROM
with the exact `LDR_77` loader. An **interrupted BootROM handshake arms the
by-design security wipe** — recovery is a 3-button reset + ~3 min autoloader
reflash (documented). Old board parked in `11011` (`FS_DIRTY_ALL` RPMB-backed).

**stage3 payload exploit (tracked):** the imggen conversion kit's secure boot
image ships BBAndroids' `passport_stage3` payload — it re-enters the PBL in
debug mode (`BOOT_PARTITION_SELECT=0x5D1`) with a replacement PBL that **skips
SBL authentication** and loads the GPT-selected `bbss` partition (type GUID
`…251C3E99`). Decoded + tracked in the Passport repo
(`notes/session31-stage3-payload-exploit.md`).
