# Appendix A: Device Specifications

## BlackBerry Classic (SQN100-1)

| Attribute | Value |
|---|---|
| SoC | Qualcomm MSM8960 (secboot3) |
| CPU | Dual-core Krait |
| GPU | Adreno 225 |
| RAM | 2 GB |
| Storage | 16 GB eMMC + microSD |
| Display | 3.5" 720×720 IPS LCD |
| Keyboard | Physical QWERTY |
| HWID | `0x9700270a` |
| Board codename | mockingbird / ontario |
| QNX Build | `QNX BLACKBERRY-528E` |
| Builder | `ec_agent` |
| eMMC | Toshiba 032GE4 (32 GB) |
| Modem | Qualcomm (Qualcomm PBL ROM, MDM9x15) |
| OS | BB10 / QNX |
| Security | ECDSA P-256 boot chain, dm-verity, Pathtrust, BIDE, SELinux, grsec/PaX |

### Embedded Source Path

```
/mnt/data/mstuglik_l/e7_boot/boot_images/1.0.x/core/boot/secboot3/msm8960/sbl1/...
/mnt/data/mstuglik_l/e7_boot/boot_images/1.0.x/core/boot/secboot3/common/...
```

## BlackBerry Passport (SQW100-1)

| Attribute | Value |
|---|---|
| SoC | Qualcomm MSM8974AA (Snapdragon 800) |
| CPU | Quad-core Krait 400 |
| GPU | Adreno 330 |
| RAM | 3 GB |
| Storage | 32 GB eMMC + microSD |
| Display | 4.5" 1440×1440 IPS LCD |
| Keyboard | Physical QWERTY (touch-sensitive) |
| HWID (EMEA) | `0x87002c0a` |
| HWID variants | `0x84002c0a` (NA/SQW100-3), `0x85002c0a` (VZW/SQW100-2), `0x86002c0a` (Sprint), `0x8c002c0a` (Wichita) |
| Oslo variants | `0x8d/8e/8f002c0a` (windermere2/3/4, SQW100-4/ROW) |
| Board codename | WINDERMERE EMEA / "wolverine" (imggen) |
| QNX Build | `QNX BLACKBERRY-603C` |
| OS | BB10 / QNX |
| Security | Same as Classic |

## MSM8960 vs MSM8974AA Comparison

| Feature | MSM8960 | MSM8974AA |
|---|---|---|
| CPU cores | 2 (Krait) | 4 (Krait 400) |
| Max clock | 1.5 GHz | 2.3 GHz |
| GPU | Adreno 225 | Adreno 330 |
| RAM support | LPDDR2 | LPDDR3 |
| eMMC controller | SDCC | SDCC |
| USB | 2.0 | 3.0 |
| Camera ISP | Dual 18 MP | Dual 21 MP |
| Video | 1080p@30fps | 4K@30fps |
| PBL register region | `0xFCxxxxxx` (different layout) | `0xFC4xxxxx` |
| Stage3 exploit | Not applicable | `passport_stage3` (RPM→PBL) |
| EDL status | No firehose programmer available | Sahara firehose available |

## QNX MMC Driver

| Attribute | Value |
|---|---|
| Binary | `devb-sdmmc-rim-msmsdcc` |
| Type | ELF32 ARM EABI5, PIE/shared, stripped |
| Vendor | RIM (BlackBerry) fork of QNX `devb-sdmmc` |
| Instances | 2 on Classic |
| DCMD dispatch | `0x10a0d574` (Thumb) |
| compare-table | `0x10a0d644` |
| WRITE_PROTECT handler | `0x10a0fcec` |
| mmc_switch | `0x10a076c0` |
| CMD6 send | `0x10a08240` |
| ext_csd live copy | `0x10a1954f` (module-offset `0x1954f`) |

## g_Disk_Drivers Binary

| Attribute | Value |
|---|---|
| Size | 4,488 bytes |
| Format | ELF32 ARM |
| BuildID | `84c92d436dc1ffd7c62c27eccfadb2f0` |
| Permissions | `-rwxrwsrwx` (setgid) |
| Owner | `root:Disk_Drivers` |
| Groups available | ~400 (`g_nto`, `g_Disk_Drivers`, `g_pps`, `g_sys`, `g_rpmb`, `g_trustzone`, `g_powerauth`, `g_filesystem`, `g_dev0`–`g_dev99`, `g_android_*`, etc.) |
| Command | Fixed `/bin/ksh` (NOT argv-injectable) |

## __root Binary

| Attribute | Value |
|---|---|
| Size | 4,488 bytes |
| Format | ELF32 ARM |
| BuildID | `84c92d436dc1ffd7c62c27eccfadb2f0` |
| Permissions | `-rwsr-xr-x` (setuid) |
| Owner | `root:nto` |
| .text offset | `0x808` (file) |
| .rodata offset | `0xa50` (file) |
| ADN_NONROOT (plain abilities) | Thumb `0x860`: `orr r1, r1, #0x20000000` |
| ADN_NONROOT (range abilities) | Thumb `0x884`: `orr r1, r1, #0x20000000` |
| Imported functions | `procmgr_ability`, `setuid`, `setreuid`, `system` |

## mmcsdpub Binary

| Attribute | Value |
|---|---|
| Size | 23,600 bytes |
| Permissions | `750 root:nto` |
| Binary path | `/base/bin/mmcsdpub` |
| Devctl command | `DCMD_MMCSD_DEVINFO` |
| PPS default path | `/fs/pps/qnx` (wrong — real path is `/pps`) |
| Published fields | `read_only::true/false`, `write_protection::%s`, `blocks_size`, `-partition_count`, `-status`, `sector_size` |
