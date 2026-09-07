# BlackBerry BB10 Classic & Passport: Comprehensive Autoloader & Security Analysis

## 1. Device Identification

| Property | Classic (STL100-1/2/3/4) | Passport (SQW100-1/2/3/4) |
|----------|--------------------------|---------------------------|
| SoC | MSM8960 (Snapdragon S4 Plus) | MSM8974AA (Snapdragon 800) |
| Architecture | ARMv7-a (Krait 300), 32-bit | ARMv7-a (Krait 400), 32-bit |
| QNX uname | `BLACKBERRY-528E` | `BLACKBERRY-603C` |
| OS codename | CLASSICNA | WINDERMEREEMEA |
| OS version | BB10 10.3.3 (QNX 8.0.0), build 2018/02/21 | Same |
| USB RNDIS MAC | `a6:e4:b8:47:d4:4a` | `a6:e4:b8:2f:0d:8a` |
| eMMC HWID | `0x9700270a` | TBD (dump pending) |
| Boot0 build | v11.0.46.5, `ec_agent`, Jul 8 2014 | TBD |
| Secure boot | YES (field8=0) | YES (field8=0) |
| Autoloader OS | BB10 10.3.03.3216 (SQW/STA) | BB10 10.3.03.3216 (SQW) |

## 2. BB10 Autoloader Format

### 2.1 Structure Overview

BB10 autoloaders are **PE32 Windows executables** (not ZIP archives) containing a QCFM (Qualcomm Firmware Manager) payload:

```
Offset 0x000000:  MZ/PE32 header (x86, 4 sections)
                  .text   @ 0x000400  (921 KB)
                  .rdata  @ 0x0e1200  (790 KB)
                  .data   @ 0x1a6200  (7.2 MB)
                  .rsrc   @ 0x8d2a00  (1 KB)
Offset 0x8d2e00:  PE overlay (autoloader payload) = ~2910 MB
                  [0xAAAA padding]
                  [QCFM/SFI image data]
                  [QNX IFS filesystem images]
```

The PE code is ~8.8 MB; the overlay is ~2910 MB containing the actual firmware.

### 2.2 QCFM Format

QCFM (Qualcomm Firmware Manager) is BlackBerry's proprietary firmware packaging format:

- **QCFMv1**: Legacy format (BB10 10.0-10.2)
- **QCFMv2**: Current format (BB10 10.3+), with Run Records (RR) and Container Headers (CH)
- **SFI (Single File Image)**: Individual firmware components within QCFM

Key QCFM structures:
- Container Header (CH): magic, version, chunk metadata
- Run Records (RR): magic, version, section offsets
- MCT (Master Configuration Table): partition layout, device mapping
- MCT_QNX: QNX-specific partition definitions
- MCT_BOOTROM_SEC_NAND: boot chain configuration
- MCT_FLASH_CHIP / MCT_MAPPING: flash device geometry

### 2.3 Image Contents

The autoloader overlay contains (in order):
1. **QCFM archive** with SFI labels describing each image
2. **QNX IFS (Initial File System)** images containing:
   - Shell scripts (`/base/scripts/ota_info_pps.sh`, `btool`, etc.)
   - System binaries (`/base/bin/__root`, `mod_nvram`, `pathtrust`, etc.)
   - Configuration files
3. **Partition images** for each flash region
4. **Signatures and certificates** (PROD-signed for secure devices)

### 2.4 Key Differences from Priv/Android Autoloaders

| Aspect | BB10 (Classic/Passport) | Priv/Android (MSM8992) |
|--------|------------------------|----------------------|
| Format | PE32 + QCFM/SFI | ZIP with fastboot images |
| OS | QNX Neutrino 8.0.0 | Android 6.0.1 |
| Flash tool | Custom autoloader.exe | fastboot |
| Images | IFS, PFS, MCT | boot.img, system.img, recovery.img |
| Boot chain | SBL1→BBSS→Stage1-3→Aboot | SBL1→Aboot→boot.img |
| Security | Secure boot + pathtrust | dm-verity + SELinux |

## 3. Boot Chain (BB10)

### 3.1 Boot Sequence

```
PBL (ROM) → SBL1 (Primary Boot Loader)
  → BBSS (BlackBerry Boot Security Services)
    → Stage1 → Stage2 → Stage3 (prototype bootloader stages)
      → Aboot (Android Boot Loader, repurposed for QNX)
        → IFS (QNX Initial File System)
          → Startup scripts → /base/bin/startup → OS
```

### 3.2 Boot GPT Layout (boot partition)

```
Partition    LBA Range          Size
─────────────────────────────────────
hwi          34-41              4 KB      (Hardware Info)
stage1       42-297             128 KB    (SBL1 stage 1)
stage2       298-937            320 KB    (SBL1 stage 2)
stage3       938-953            8 KB      (SBL1 stage 3)
bbss         954-1209           128 KB    (Boot Security Services)
sbl1r        1210-1849          320 KB    (SBL1 recovery)
tzr          1850-2873          512 KB    (TrustZone recovery)
rpmr         2874-3385          256 KB    (RPM recovery)
sdir         3386-3513          64 KB     (SDI recovery)
abootr       3514-7609          2048 KB   (Aboot recovery)
```

### 3.3 User GPT Layout (main eMMC)

```
Partition    LBA Range          Size        Notes
──────────────────────────────────────────────────
gsign        34-39              6 sectors   (GPT signature)
mct_b        40-47              8 sectors   (MCT backup)
pad          48-127             80 sectors
nvram        128-8191           3.9 MB      (NVRAM store)
calwork_b    8192-65535         28 MB       (calibration working)
dmi_b        65536-131071       32 MB       (DMI backup)
calback_b    131072-262143      64 MB       (calibration backup)
aboot        262144-270335      4 MB        (Aboot)
sbl1         270336-272383      1 MB        (SBL1)
rpm          272384-273407      0.5 MB      (RPM)
tz           273408-274431      0.5 MB      (TrustZone)
sdi          274432-275455      0.5 MB      (SDI)
fsc          278528-281599      1.5 MB      (File System Config)
modemst1     281600-284671      1.5 MB      (Modem Status 1)
modemst2     284672-287743      1.5 MB      (Modem Status 2)
blog         287744-288255      0.2 MB      (Boot Log)
perm         288256-288767      0.2 MB      (Permissions)
nvuser       288768-289279      0.2 MB      (NV User)
ddr          289280-289343      64 sectors  (DDR config)
bkup_ddr     289344-289407      64 sectors  (Backup DDR)
prdid        294912-295415      0.2 MB      (Product ID)
boardid      295424-295927      0.2 MB      (Board ID)
fsg          295936-299007      1.5 MB      (File System G)
ssd          311296-313343      1 MB        (Secure Storage)
metadata     313344-315391      1 MB        (Metadata)
frp          315392-317439      1 MB        (Factory Reset Protection)
bcota        327680-335871      4 MB        (BC OTA)
rcause       335872-368639      16 MB       (Reset Cause)
spare        368640-393215      12 MB       (Spare)
persist      393216-458751      32 MB       (Persist)
crypto       458752-524279      32 MB       (Crypto)
ares         524280-524287      8 sectors
boot         524288-589823      32 MB       (Boot/IFS)
recovery     589824-655359      32 MB       (Recovery)
modem        655360-802815      72 MB       (Modem)
system       802816-6045695     2560 MB     (System/PFS)
cache        6045696-8142847    1024 MB     (Cache)
userdata     8142848-8142848    1 sector    (Userdata)
```

## 4. Security Mechanisms

### 4.1 Secure Boot

Both Classic and Passport have **secure boot enabled** (field8=0 in build-info):
- SBL1 is signature-verified by PBL
- Each subsequent stage verifies the next
- OS (IFS/PFS) images are signature-verified
- **Bypassed by**: `bbss.insecure` flag (field8=1 in build-info @ boot0 offset 0x35a98)
- When insecure flag is set: "Insecure mode, Skipping OS Signature verification"

### 4.2 PathTrust

QNX's `pathtrust` mechanism controls which executables are trusted:

```bash
/pathtrust <file>        # Trust the underlying filesystem
/pathtrust !<file>       # Trust THAT SPECIFIC FILE
/pathtrust -t <file>     # Report trust state ('trusted'/'untrusted')
/pathtrust lockdown      # Freeze the trust list
```

- Requires root to modify (running as `nto` gives "sending trust failed: 1")
- Trust list is re-applied every time `btool` runs (boot autoroot + switchzone)
- Does NOT persist on its own — `btool` re-whitelists each boot
- The `btool` script contains hardcoded pathtrust whitelist entries

### 4.3 eMMC Write-Protect

- **boot0/boot1**: Hardware write-protected (`B_PWR_WP_EN` ext_csd[0xAD]=0x04)
  - Returns EROFS even as uid-0
  - Enforced at eMMC controller level, NOT by DAC/SELinux
  - Toggling requires MMC CMD6/ext_csd access (needs patched MMC driver)
- **User area** (os0, uda0, dmi0): WRITABLE as root
- **RPMB**: "Inappropriate I/O control" — authenticated access only

### 4.4 Boot Slot Mechanism

BB10 uses dual boot slots (A/B):
- `switchzone` trigger swaps active slot
- Dropping dev-mode + SSH on slot switch
- Recovered by reboot + re-enable Development Mode
- `btool` runs during switchzone for migration scripts

## 5. Root & Exploit Methods

### 5.1 getroot Rootkit (Confirmed Working)

The pre-rooted autoloaders use the **getroot** rootkit:

1. **getroot payload**: `/base/scripts/ota_info_pps.sh` → symlink to `btool`
2. **btool** runs AS ROOT at boot (autoroot) and on switchzone
3. **btool** whitelists files via pathtrust:
   ```
   /proc/boot/pathtrust !/accounts/devuser/rootdata/launcher_patcher
   /proc/boot/pathtrust !/base/bin/mod_nvram
   /proc/boot/pathtrust !/base/bin/__root    # ADDED for uid-0 root
   ```
4. **__root** (setuid-0, 4488-byte ELF) spawns interactive uid-0 ksh

### 5.2 Real UID-0 Root (Achieved 2026-08-30)

Full chain:
```
getroot autoroot → btool (as root) → pathtrust whitelist !/base/bin/__root
  → __root (suid-0) → interactive uid-0 ksh
```

Verified capabilities:
- Write to `/root/` (confirmed)
- Read all `/dev/emmc/*` (boot0, boot1, nvram0, rpmb0, dmi0)
- Full filesystem access (except boot0/boot1 which are hardware WP)

### 5.3 mod_nvram Tool

The `mod_nvram` tool (from bb10root-tools) provides NVRAM manipulation:

```c
// Key NVRAM operations
nv_delete_insecure(blockid)      // Delete insecure NVRAM record
nv_delete_secure(blockid)        // Delete secure NVRAM record
nv_get_record(blockid, buf, sz)  // Read NVRAM record
nv_write_record(blockid, buf, sz)// Write NVRAM record
nv_is_protected(blockid)         // Check if record is protected
GetBootromMetrics(buf)           // Read bootrom metrics
readOSMetrics()                  // Read OS metrics
```

Key NVRAM block IDs:
- `0x2819`: OS BLOCK (delete for downgrade)
- `0x2852`: RADIO BLOCK (delete for downgrade)

### 5.4 Passport Stage3 Exploit (MSM8974AA)

The `passport_stage3` tool exploits the MSM8974AA PBL debug mode:

1. **RPM component**: Sets `BOOT_PARTITION_SELECT=0x5D1` and `GCC_WDOG_DEBUG=0x20000`, resets APPS
2. **APPS component**: Reimplements PBL boot with stubbed `pbl_authenticate_sbl()` (returns 0, skips signature verification)
3. Uses PBL ROM function pointers directly at addresses:
   - `0xfc100080`: RPM data
   - `0xfe800000`: APPS code
   - `0xfe820000`: APPS data

### 5.5 PathTrust Full Unlock

The `unlock_path_trust.zip` (public, 8960/10.3.3.3216) provides full pathtrust bypass:
- Available for Classic (MSM8960) with BB10 10.3.3.3216
- Removes all pathtrust restrictions

## 6. imggen: Prototype BB10 Bootloader Generator

### 6.1 Overview

The `imggen` tool (BBAndroids, GPL) generates prototype BB10 bootloader images from stock boot0/user dumps:

```
imggen/
├── main.py          # Main entry point, build orchestration
├── bb.py            # Build info parser, HWI generator
├── gpt.py           # GPT encoder/decoder
├── mct.py           # MCT partition parser
├── utils.py         # Utility functions
└── files/           # Template binaries
    ├── sbl1.mbn     # SBL1 template (488 KB, ARM ELF)
    ├── bbss.mbn     # BBSS template (248 KB, ARM ELF)
    ├── stage1.mbn   # Stage 1 (91 KB)
    ├── stage2.mbn   # Stage 2 (145 KB)
    ├── stage3.mbn   # Stage 3 (122 KB, ARM ELF)
    ├── aboot.mbn    # Aboot (1.1 MB, ARM ELF)
    ├── tz.mbn       # TrustZone (89 KB, ARM ELF)
    ├── rpm.mbn      # RPM (120 KB, ARM ELF)
    ├── sdi.mbn      # SDI (11 KB, raw ARM code)
    ├── sbl1r.mbn    # SBL1 recovery (500 KB)
    ├── NON-HLOS.bin # Non-HLOS firmware (1.8 MB)
    ├── boot_gpt_secure.bin   # Secure boot GPT (2560 bytes)
    ├── boot_gpt_insecure.bin # Insecure boot GPT (2560 bytes)
    ├── user_gpt.bin          # User GPT (31 MB)
    ├── blog.img      # Boot log image
    ├── boardid.img   # Board ID image
    ├── nvuser.img    # NV user image
    ├── perm.img      # Permissions image
    └── prdid.img     # Product ID image
```

### 6.2 Key Behaviors

From `bb.py` build_info parser:
- Reads `RIM BlackBerry Device` header from boot0 at known offset
- Extracts HWID, version, builder, date, secure flag
- Parses MCT (Master Configuration Table) and revision table
- Generates HWI (Hardware Info) partition with device-specific data

From `gpt.py`:
- Generates GPT partition tables for both boot and user areas
- Secure vs insecure GPTs differ at byte 529 (GPT partition table CRC)
- User GPT defines all device partitions (nvram, aboot, sbl1, etc.)

From `mct.py`:
- Parses MCT partition entries from stock dumps
- Maps partition names to LBA ranges
- Handles both secure and insecure MCT variants

### 6.3 BBSS Strings (Key Insight)

The `bbss.mbn` template contains critical strings revealing the boot security architecture:

```
bbss_insecure          # Flag: insecure device mode
bbss_wp_type           # Write-protect type identifier
backup_bc_ver          # Backup boot chain version
Debug board switch forcing backup boot chain
Failed to load primary SBL, will load backup SBL instead
Jump to SBL            # Primary boot chain handoff
Jump to AB00T          # Aboot handoff
Jump to core0          # Core0 handoff
Backup boot key combo active
BCB indicates update is available
```

This reveals:
- BBSS manages primary/backup boot chain selection
- "Debug board switch" can force backup boot chain
- BCB (Boot Control Block) indicates OTA update availability
- Backup boot chain is the recovery path

## 7. Current Status & Blockers

### 7.1 Achieved

- ✅ Real uid-0 root on Classic (via pathtrust whitelist + __root)
- ✅ Real uid-0 root on Passport (same method)
- ✅ Full eMMC read access (boot0, boot1, nvram0, rpmb0, dmi0)
- ✅ BerryCore 0.88.0 + Python 3.11.10 + BerryPy installed
- ✅ SSH access via devuser + blackberry-connect tunnel
- ✅ All pre-rooted autoloaders extracted and analyzed

### 7.2 Blockers for LineageOS

1. **boot0 hardware write-protect**: `B_PWR_WP_EN` (ext_csd[0xAD]=0x04)
   - Requires MMC driver patch (sdmmc.zip, PRIVATE/Patreon) to toggle via CMD6
   - Or ISP/desolder approach (Balika method)
2. **PathTrust full unlock**: Available (unlock_path_trust.zip, public)
3. **Prototype bootloader**: Available (imggen, free/open-source)
4. **"bbss.insecure" flag**: Must be pinned to 1 in build-info @ boot0 offset 0x35a98

### 7.3 Remaining Steps for LineageOS

```
1. PathTrust full unlock (unlock_path_trust.zip)
2. MMC driver patch → toggle boot0 BOOT_WP
3. Write boot0@0x35a98=1 (bbss.insecure flag)
4. Flash prototype bootloader (imggen output)
5. Reboot → LineageOS
```

## 8. Research Tools & Resources

### 8.1 On-Device Tools

| Tool | Location | Purpose |
|------|----------|---------|
| `__root` | `/base/bin/__root` | Setuid-0 root shell |
| `btool` | `/apps/sys.android.*.ns/native/system/xbin/btool` | Boot tool (pathtrust whitelist) |
| `mod_nvram` | `/base/bin/mod_nvram` | NVRAM manipulation |
| `pathtrust` | `/proc/boot/pathtrust` | Path trust management |
| `pidin` | `/proc/boot/pidin` | Process listing |
| `ota_info_pps.sh` | `/base/scripts/ota_info_pps.sh` | getroot autoroot payload |

### 8.2 Host Tools

| Tool | Location | Purpose |
|------|----------|---------|
| `blackberry-connect` | BB10 NDK host tools | SSH tunnel to device |
| `login.py` | `/tmp/pp/login.py` | Paramiko SSH helper |
| `up.py` | `/tmp/pp/up.py` | SFTP upload helper |
| `connect_auth.sh` | `/tmp/pp/connect_auth.sh` | Tunnel restart script |

### 8.3 Source Code

| Repository | Path | Purpose |
|------------|------|---------|
| imggen | `/home/stanw47/priv-research/imggen/` | BB10 prototype bootloader generator (GPL) |
| passport_stage3 | `/home/stanw47/priv-research/passport_stage3/` | MSM8974AA PBL debug exploit (GPL) |
| bb10root-tools | `/home/stanw47/priv-research/bb10root-tools/` | NVRAM manipulation tools |
| sdmmc-driver | `/home/stanw47/priv-research/sdmmc-driver/` | MMC driver for CMD6 access |

## 9. Appendix: Key Memory Addresses

### 9.1 MSM8960 (Classic)

- Build-info secure field8: boot0 offset `0x35a98`, nvram0 copy `0x18098`
- `__root` ELF: entry `0xfe800000` area (mapped by stage3)

### 9.2 MSM8974AA (Passport)

- `passport_stage3` targets:
  - `0xfc100080`: RPM data
  - `0xfe800000`: APPS code
  - `0xfe820000`: APPS data
- `GCC_WDOG_DEBUG=0x20000`: Watchdog debug register
- `BOOT_PARTITION_SELECT=0x5D1`: Boot partition selection

### 9.3 QNX Ability Definitions (procmgr.h)

```
PROCMGR_AID_MEM_PHYS      = 16  # Physical memory mapping
PROCMGR_AID_PATH_TRUST    = 40  # Path trust management
PROCMGR_AID_IO            = 31  # I/O access
PROCMGR_ADN_ROOT          = 0x10000000  # Root ability domain
PROCMGR_ADN_NONROOT       = 0x20000000  # Non-root ability domain
PROCMGR_AOP_ALLOW         = 0x00020000  # Allow operation
PROCMGR_AOP_DENY          = 0x00010000  # Deny operation
```
