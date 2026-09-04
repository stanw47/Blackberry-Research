# Appendix C: Filesystem Mounts

## Complete Mount Table

| Device | Mount Point | FS Type | Options | Notes |
|---|---|---|---|---|
| — | `/` | qnx6 | ro, trusted | Root filesystem |
| `/dev/emmc/os0t179` | `/base` | rcfs | ro | OS boot scripts/config |
| `/dev/emmc/radio0t179` | `/radio` | rcfs | ro | Modem firmware |
| `/dev/emmc/user0` | `/` | qnx6 | ro, trusted | Root (same device as /) |
| `/dev/emmc/user0` | `/sdcard` | qnx6 | — | SD card mount |
| `/dev/emmc/user0` | `/data` | qnx6 | forceencrypt | User data (NOT trusted) |
| `/dev/emmc/cal_work0` | `/efs` | qnx6 | — | Calibration data |
| `/dev/emmc/sd0` | `/accounts/1000/removable/sdcard` | dos/fat32 | — | External SD card |
| boot0 / boot1 | (not mounted) | raw | — | Raw boot partitions |
| `/dev/emmc/rpmb0` | (not mounted) | raw | — | RPMB |

## Filesystem Hierarchy

```
/                           (qnx6, ro, trusted)
├── base/                   (rcfs from os0t179, ro)
│   ├── bin/                (rcfs — system binaries)
│   │   ├── __root          (setuid-0, 4488B ELF)
│   │   ├── g_Disk_Drivers  (setgid, 4488B ELF)
│   │   ├── g_nto           (setgid)
│   │   ├── g_pps           (setgid)
│   │   ├── mmcsdpub        (23600B, root:nto)
│   │   ├── pidin           (process info)
│   │   ├── dd              (disk dump)
│   │   ├── cat             (concatenate)
│   │   └── ...             (other system binaries)
│   ├── scripts/
│   │   └── ota_info_pps.sh # Autoroot entry point
│   ├── dev/                (device nodes)
│   ├── etc/                (configuration)
│   ├── lib/                (libraries)
│   └── proc/               (procfs mount point)
│       └── pathtrust       (pathtrust trust list, root:nto 750)
├── accounts/
│   └── 1000/
│       └── removable/
│           └── sdcard/     (FAT32, external SD)
├── data/                   (qnx6, forceencrypt, NOT trusted)
├── dev/
│   └── emmc/
│       ├── boot0           (4MB, EROFS)
│       ├── boot1           (4MB, EROFS)
│       ├── rpmb0           (RPMB)
│       ├── nvram0          (4,128,768B, writable)
│       ├── dmi0            (1MB, writable)
│       ├── os0             (writable)
│       ├── os1             (writable)
│       ├── uda0            (writable)
│       ├── user0           (writable)
│       ├── cal_work0       (writable)
│       ├── radio0          (writable)
│       ├── sd0             (SD card)
│       ├── hd0 → boot0     (symlink)
│       ├── hd1 → boot1     (symlink)
│       ├── hd2 → rpmb0     (symlink)
│       ├── hd3 → nvram0    (symlink)
│       ├── hd4 → cal_work0 (symlink)
│       ├── hd5 → dmi0      (symlink)
│       ├── hd6 → os0/os1   (symlink)
│       └── hd7 → uda0      (symlink)
├── efs/                    (qnx6, calibration)
├── radio/                  (rcfs from radio0t179, ro)
├── proc/                   (procfs)
│   └── <pid>/
│       ├── as              (address space, ability-gated)
│       ├── cmdline         (command line)
│       ├── ctl             (process control)
│       └── ...
└── pps/                    (Persistent Publish/Subscribe)
```

## Pathtrust Trust List

`/proc/boot/pathtrust` (root:nto, mode 750):

```
<file>         # trust filesystem
!<file>        # trust specific file
-t <file>      # query trust status
lockdown       # lock trust list
```

### Current Whitelist (from btool line 31)

```
!/accounts/devuser/rootdata/launcher_patcher
!/base/bin/mod_nvram
!/base/bin/__root
```

### How Trust Works

- Trust list re-applied every `btool` run (boot autoroot + switchzone)
- Not persistent by itself — re-applied on trigger
- `!<file>` makes the file "trusted" in Pathtrust LSM
- Trusted files can be executed/mmap'd by root/banned-caps processes

## Device Node Permissions

| Device | Owner | Group | Mode | Type |
|---|---|---|---|---|
| `/dev/emmc/*` | root (800) | Disk_Drivers (132) | `660` | block (`brw-rw----`) |
| `/dev/emmc` | root | root | `755` | directory |

## Access Control Paths

```
devuser (uid 850, gid 200)
  → no direct access to /dev/emmc/* (EPERM)
  → via g_Disk_Drivers (setgid 132):
      egid=132 → /dev/emmc/* opens (DAC allows)
      → devctl channel to sdmmc driver
      → CARD_REGISTER, ext_csd read
      → WRITE_PROTECT → mmc_switch → EIO (card rejects)
```

```
root (uid 0)
  → /dev/emmc/* opens (DAC allows)
  → dd reads boot0 (succeeds)
  → dd writes boot0 → EROFS (hardware WP)
  → /proc/<pid>/as → EPERM (ability-gated on current boot)
```

## QNX6 Filesystem Properties

| Property | Value |
|---|---|
| Type | QNX6 (read-only by default) |
| Block size | 512 bytes |
| Max file size | 2^64 bytes |
| Max filename | 255 bytes |
| Journaling | No |
| Encryption | Optional (forceencrypt on /data) |

## rcfs (ROM Compact File System)

| Property | Value |
|---|---|
| Type | Read-only compressed filesystem |
| Mount | `/base`, `/radio` |
| Source | Raw eMMC partitions (`os0t179`, `radio0t179`) |
| Purpose | Boot scripts, system config, modem firmware |
| Modification | Requires reflashing the partition |
