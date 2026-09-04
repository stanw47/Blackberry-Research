# Appendix B: Partition Layouts

## eMMC Partition Map (Both Classic & Passport)

```
┌──────────────────────────────────────────────────────────────────────┐
│                         eMMC Device                                 │
├────────────┬─────────┬──────────────────────────────────────────────┤
│ Partition  │ Size    │ Contents                                     │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ boot0      │ 4 MB    │ SBL1, HWI, bbss.insecure flag               │
│            │         │ HW write-protected (EROFS)                   │
│            │         │ Sub-regions: .01000000, .02000000            │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ boot1      │ 4 MB    │ Backup SBL1                                  │
│            │         │ HW write-protected (EROFS)                   │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ rpmb0      │ —       │ Replay Protected Memory Block                │
│            │         │ Authenticated-only write                     │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ nvram0     │ 4,128,  │ NVRAM records, build-info, partition map    │
│            │ 768 B   │ "RIM BlackBerry Device" marker at 0x1801c   │
│            │         │ bbss.insecure at 0x18098                     │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ cal_work0  │ —       │ Calibration data                             │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ dmi0       │ 1 MB    │ Device/board info (DMI)                      │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ os0        │ —       │ OS slot (primary), writable                  │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ os1        │ —       │ OS slot (backup/dual-boot), writable         │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ uda0       │ —       │ User data area, writable                     │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ radio0     │ —       │ Modem firmware                               │
├────────────┼─────────┼──────────────────────────────────────────────┤
│ sd0        │ —       │ SD card                                      │
└────────────┴─────────┴──────────────────────────────────────────────┘
```

## Symlinks

```
hd0 → boot0
hd1 → boot1
hd2 → rpmb0
hd3 → nvram0
hd4 → cal_work0
hd5 → dmi0
hd6 → os0 / os1
hd7 → uda0
```

All block devices: `root:Disk_Drivers` mode `660` (`brw-rw----`).

## GPT Layout (boot0)

### Boot GPT (2,560 bytes)

| Partition | UUID | Purpose |
|---|---|---|
| `hwi` | (dynamic) | HWI text config |
| `stage1` | — | Stage 1 bootloader |
| `stage2` | — | Stage 2 bootloader |
| `stage3` | — | Stage 3 bootloader |
| `bbss` | — | BlackBerry Secure Suite |
| `sbl1r` | — | SBL1 (root) |
| `tzr` | — | TrustZone |
| `rpmr` | — | RPM firmware |
| `sdir` | — | SDI |
| `abootr` | — | Aboot (LK) |

### GPT Templates (imggen)

| File | Size | Differs At |
|---|---|---|
| `boot_gpt_secure.bin` | 2,560 B | — |
| `boot_gpt_insecure.bin` | 2,560 B | Byte 529 (GPT ptable CRC) |

## User Area GPT (uda0)

| Partition | Purpose |
|---|---|
| `nvram` | NVRAM |
| `calwork_b` / `calback_b` | Calibration work/backup |
| `aboot` / `sbl1` / `rpm` / `tz` / `sdi` | Bootloader components |
| `blog` / `boardid` / `nvuser` / `perm` / `prdid` | BB config/identity |
| `modem` | NON-HLOS modem firmware |

## NVRAM Partition Map (nvram0)

Named partitions in the BB10/QNX map:

| Partition | Purpose |
|---|---|
| `nvram` | NVRAM records |
| `cal_work` | Calibration work area |
| `cal_backup` | Calibration backup |
| `dmi_mbr/sig/fsys` | Device info MBR/signature/filesystem |
| `os_mbr/sig/fsys` | OS MBR/signature/filesystem |
| `system` | System partition |
| `radio` | Modem partition |
| `user` | User data |

## Build Info Structure

Found at `boot0` offset `0x35a1c` (Classic) and `nvram0` offset `0x1801c`:

```
Offset  Field
0x00    version (u32)
0x04    size (u32)
0x08    magic "RIM BlackBerry Device" (4s)
0x0c    platform (u32)
0x10    hwid (u32)
...     (padded struct)
0x7c    field8 (u32) = bbss.insecure flag
```

**`_BUILD_INFO_FORMAT`**: `"<II4sI64s16s16s12sII...x22...40s1024s>"`

### Classic Values

| Location | Offset | Value | Meaning |
|---|---|---|---|
| boot0 | `0x35a1c` | `"RIM BlackBerry Device"` | build-info start |
| boot0 | `0x35a98` | `0x00000000` | **SECURE** |
| nvram0 | `0x1801c` | — | build-info start |
| nvram0 | `0x18098` | `0x00000001` | **INSECURE** (getroot artifact) |

## Dump Checksums (Classic)

| Dump | Size | MD5 (partial) |
|---|---|---|
| `boot0.img` | 4,194,304 B | `d6a15e39…` |
| `boot1.img` | 4,194,304 B | `b5cfa9d6…` |
| `nvram0.img` | 4,128,768 B | — |
| `dmi0.img` | 1,048,576 B | — |

## ext_csd Boot Write-Protect (Live)

| Byte | Field | Value | Meaning |
|---|---|---|---|
| `0xAA` | `BOOT_CONFIG_PROT` | `0x00` | NOT fused — temporary, clearable |
| `0xAD` | `B_BOOT_WP` | `0x04` | `B_PWR_WP_EN` set |
| `0xB3` | `BOOT_WP_STATUS` | `0x08` | Reflects B_PWR_WP_EN |

### WP Type Semantics

| Type | Byte | Persistence | Re-armed By |
|---|---|---|---|
| `B_PWR_WP_EN` | ext_csd[173] bit 2 | Temporary (power-on) | SBL1 every boot |
| `BOOT_CONFIG_PROT` | ext_csd[170] | Permanent (irreversible) | Never |
| `B_PERM_WP_EN` | ext_csd[173] bit 0 | Permanent | Never |
| `PERM_PSWD_DIS` | ext_csd[171] | Permanent | Never |
