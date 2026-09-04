# Appendix G: Glossary

## Hardware

| Term | Definition |
|---|---|
| **MSM8960** | Qualcomm Snapdragon S4 Plus, dual-core Krait, used in BlackBerry Classic |
| **MSM8974AA** | Qualcomm Snapdragon 800, quad-core Krait 400, used in BlackBerry Passport |
| **eMMC** | Embedded Multi-Media Controller — integrated flash storage |
| **SDCC** | Snapdragon Digital Card Controller — eMMC/SD host controller |
| **RPMB** | Replay Protected Memory Block — authenticated eMMC partition |
| **HWID** | Hardware ID — unique identifier burned into SoC fuses |
| **SoC** | System on Chip |

## Boot Chain

| Term | Definition |
|---|---|
| **PBL** | Primary Boot Loader — immutable ROM code, root of trust |
| **SBL1** | Secondary Boot Loader — signed, stored in boot0/boot1 |
| **aboot** | Android Bootloader — LK (Little Kernel) fork |
| **LK** | Little Kernel — minimal bootloader framework |
| **bbss** | BlackBerry Secure Suite — sets insecure flag, manages secure boot |
| **IFS** | Initial File System — ramdisk mounted during early boot |
| **rpm** | Remote Processor Manager — co-processor firmware |
| **tz** | TrustZone — ARM secure world firmware |
| **sdi** | Secure Debug Image |
| **ECDSA** | Elliptic Curve Digital Signature Algorithm |
| **P-256** | NIST curve used for boot chain signing |

## eMMC

| Term | Definition |
|---|---|
| **boot0** | Boot partition 0 — contains SBL1, 4 MB, HW write-protected |
| **boot1** | Boot partition 1 — backup SBL1, 4 MB, HW write-protected |
| **uda0** | User Data Area — main storage, writable |
| **nvram0** | Non-Volatile RAM — build-info, partition map, 4.1 MB |
| **dmi0** | Desktop Management Interface — device/board info, 1 MB |
| **ext_csd** | Extended Card-Specific Data — eMMC configuration register |
| **CMD6** | SWITCH command — writes ext_csd bytes |
| **B_PWR_WP_EN** | Boot Power-On Write Protect Enable — temporary, re-armed by SBL1 |
| **BOOT_CONFIG_PROT** | Boot Configuration Protection — permanent, irreversible |
| **SWITCH_ERROR** | eMMC error returned when CMD6 is rejected |

## QNX

| Term | Definition |
|---|---|
| **rcfs** | ROM Compact File System — read-only compressed filesystem |
| **qnx6** | QNX6 filesystem — main read/write filesystem |
| **procfs** | Process filesystem — `/proc/` virtual filesystem |
| **PPS** | Persistent Publish/Subscribe — QNX IPC mechanism |
| **procmgr_ability** | QNX process ability grant system call |
| **MAP_DEVICE** | Ability required for physical memory mapping |
| **MAP_PHYS** | Physical memory mapping capability |
| **MEM_PHYS** | Memory physical mapping ability — required for /proc/as |
| **DCMD** | Device Control Message — QNX devctl interface |
| **devctl** | Device control — QNX system call for driver communication |
| **device manager** | QNX userspace process that owns hardware |

## Security

| Term | Definition |
|---|---|
| **Pathtrust** | QNX filesystem trust LSM — enforces exec/mmap/module gates |
| **BIDE** | BlackBerry Integrity Detection Engine — audit-only LSM |
| **SELinux** | Security-Enhanced Linux — mandatory access control |
| **dm-verity** | Device-mapper integrity — block-level filesystem verification |
| **GRSEC** | GRsecurity — Linux kernel security patch set |
| **PaX** | PaX — memory protection patch (part of GRSEC) |
| **UDEREF** | User/Kernel pointer separation (PaX feature) |
| **PAX_REFCOUNT** | Atomic reference counting overflow protection |
| **QSEE** | Qualcomm Secure Execution Environment |
| **QSEECOM** | QSEE Communication — kernel/userspace interface |

## Exploit Concepts

| Term | Definition |
|---|---|
| **getroot** | Root exploit payload for BB10 devices |
| **btool** | Boot tool — root payload orchestrator script |
| **autoroot** | Boot-time root mechanism via btool |
| **pathtrust whitelist** | Trick: add file to /proc/boot/pathtrust to make it "trusted" |
| **group wrapper** | setgid binary that grants group membership |
| **bbss.insecure** | Flag at boot0@0x35a98 — when set, skips SBL1 verification |
| **stage3** | PBL debug mode exploit for MSM8974AA |
| **EDL** | Emergency Download Mode — Qualcomm unbricking protocol |
| **Sahara** | Qualcomm EDL handshake protocol |
| **firehose** | Qualcomm EDL flash programmer |
| **ISP** | In-System Programming — chip-out without desoldering |
| **ISP test points** | Direct eMMC access points on PCB |

## Research Terms

| Term | Definition |
|---|---|
| **RE** | Reverse Engineering |
| **Ghidra** | NSA reverse engineering tool |
| **r2** | radare2 — reverse engineering framework |
| **capstone** | Multi-architecture disassembly framework |
| **Thumb-2** | ARM Thumb-2 instruction encoding (16/32-bit) |
| **ELF** | Executable and Linkable Format |
| **BuildID** | ELF unique identifier for binary correlation |
| **PIE** | Position-Independent Executable |
| **GPT** | GUID Partition Table |
| **MCT** | Master Configuration Table |
| **HWI** | Hardware Information — text config in boot GPT |

## Filesystem

| Term | Definition |
|---|---|
| **FUSE** | Filesystem in Userspace — vtnvfsd uses this |
| **vtnvfs** | BlackBerry token filesystem — FUSE over block-based format |
| **nvuser** | Non-volatile user partition — stores security tokens |
| **hlos_unsigned.tkn** | Unsigned token file — checked by aboot for dev mode |
| **dm-verity** | Device-mapper integrity verification |

## Utilities

| Term | Definition |
|---|---|
| **pidin** | QNX process info utility |
| **slog2info** | QNX system log reader |
| **btool** | BlackBerry tool — boot-time root orchestrator |
| **mmcsdpub** | MMC/SD publisher — reads DEVINFO, publishes to PPS |
| **imggen** | Image generator — creates prototype bootloader images |
| **blackberry-connect** | Java tool — establishes SSH tunnel to device |
