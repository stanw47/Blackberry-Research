# Appendix D: Devctl Constants

## QNX MMC Devctl Encoding

```
dcmd = (sizeof<<16) + (class<<8) + cmd + 0xC0000000

Where:
  sizeof  = structure size in bytes
  class   = _DCMD_CAM (0x0C)
  cmd     = command number within _SIM_MMCSD (3600) or _SIM_SDMMC (3700)
  0xC0000000 = _DIOTF flag (device I/O, to-func)
```

## Standard Devctl Constants

```c
#define _DCMD_CAM       0x0C
#define _SIM_MMCSD      3600
#define _SIM_SDMMC      3700

// MMCSD commands (class 0x0C, base 3600)
DCMD_MMCSD_GET_CID         = 0xC0101A00  // _DIOTF(0x0C, 3600+0,  16 bytes)
DCMD_MMCSD_WRITE_PROTECT   = 0xC0201A11  // _DIOTF(0x0C, 3600+17, 32 bytes)
DCMD_MMCSD_GET_CSD         = 0xC0C81A02  // _DIOTF(0x0C, 3600+2,  200 bytes)
DCMD_MMCSD_ERASE           = 0xC0201A13  // _DIOTF(0x0C, 3600+19, 32 bytes)
DCMD_MMCSD_CARD_REGISTER   = 0xC0181A14  // _DIOTF(0x0C, 3600+20, 24 bytes)
DCMD_MMCSD_GET_ECCERR_ADDR = 0xC0041A05  // _DIOTF(0x0C, 3600+5,  4 bytes)
DCMD_MMCSD_VUC_CMD         = 0xC0441A16  // _DIOTF(0x0C, 3600+22, 68 bytes)
```

## Devctl Structure Layouts

### DCMD_MMCSD_WRITE_PROTECT (32 bytes)

```c
struct mmc_wp {
    uint32_t action;    // +0x00: CLR=0x00, SET=0x01
    uint32_t mode;      // +0x04: PWR_WP_EN=0x01
    uint64_t lba;       // +0x08: starting LBA
    uint64_t nlba;      // +0x10: number of LBAs
    uint64_t rsvd2;     // +0x18: reserved
};
```

### DCMD_MMCSD_CARD_REGISTER (24 bytes)

```c
struct mmc_card_reg {
    uint8_t  cid[16];   // +0x00: Card IDentification
    uint32_t ocr;       // +0x10: Operating Conditions Register
    uint16_t rca;       // +0x14: Relative Card Address
};
```

### DCMD_MMCSD_VUC_CMD (68 bytes)

```c
struct mmc_vuc_cmd {
    uint32_t cmd;        // +0x00: MMC command index
    uint32_t arg;        // +0x04: command argument
    uint32_t flags;      // +0x08: command flags
    uint32_t blksz;      // +0x0C: block size
    uint32_t blocks;     // +0x10: number of blocks
    uint8_t  data[48];   // +0x14: data buffer (for read/write)
};
```

## Driver Dispatch Table

### Location

- Dispatch function: `0x10a0d574` (Thumb)
- Compare table: `0x10a0d644`
- Table entry format: `(dcmd, handler)` pairs

### Registered Handlers

| dcmd | Handler Address | Function |
|---|---|---|
| `0xc0181a14` | `0x10a0d492` | CARD_REGISTER |
| `0xc0201a11` | `0x10a0fcec` | WRITE_PROTECT |
| `0xc0201a13` | `0x10a0fdb4` | ERASE / group |
| `0x40011a46` | `0x10a0d620` | ext_csd byte 0xa8 (read only) |
| `0x40101a44` | `0x10a0d5f2` | CID |
| `0xc0441a16` | **ABSENT** | VUC_CMD → ENOTTY |

### WRITE_PROTECT Handler Internals (`0x10a0fcec`)

```
Entry:
  r6 = dev_obj + target*0x2c8 + lun*0x58 + 0x1d0

Worker (0x10a0f48c):
  Gate: cmp.w sl, #0x1c → need sl==0x1c (28) for mmc_switch branch
  r5 & 7 == 0 → USER_WP:
    mmc_switch(hba, 1, 3, 0xab, val)    // ext_csd[171] USER_WP
  r5 == 2 → BOOT_WP:
    mmc_switch(sb, 1, 3, 0xad, val)     // ext_csd[173] B_BOOT_WP

Availability gate (0x10a0e53a):
  Returns non-1 for boot partitions → sets handler return to 5 (EIO)
  Reads flag at [r6 + 0x1d0 + 0x1f8] (heap-allocated)
```

### mmc_switch Call Chain

```
mmc_switch = 0x10a076c0
  → lock:     0x10a053b0
  → CMD6 send: 0x10a08240
  → unlock:   0x10a053b0
```

Required call: `mmc_switch(hba, r1=1, r2=3, r3=0xad, value=0)`

### ext_csd Live Copy

Base address: `0x10a1954f` (module-offset `0x1954f`)

| Offset | Field | Value | Meaning |
|---|---|---|---|
| `+0xa8` | BOOT_CONFIG_SUPPORT | — | Read via 0x40011a46 |
| `+0xaa` | BOOT_CONFIG_PROT | `0x00` | NOT fused |
| `+0xad` | B_BOOT_WP | `0x04` | B_PWR_WP_EN set |
| `+0xb3` | BOOT_WP_STATUS | `0x08` | Reflects B_PWR_WP_EN |

## DCMD_MMCSD_DEVINFO (mmcsdpub)

Used by `mmcsdpub` to read device information and publish to PPS:

```c
struct mmc_devinfo {
    char read_only[8];      // "true" or "false"
    char write_protection[32]; // WP status string
    uint32_t blocks_size;   // block size
    uint32_t partition_count;
    char status[32];
    uint32_t sector_size;
};
```

## RIM RAM Loader Commands

Available at the SBL/bootloader level:

| Command | Purpose |
|---|---|
| `0x20` | Persistent data struct |
| `0x21` | Bootrom log |
| `0x50` | TZ info |
| `0xB1` | Flash IDs |
| `0xB4` | Flash regions info |
| `0xB5` | Flash info |
| `0xD9` | MCT (Master Configuration Table) |
| `0xDA` | HIS |
| `0xDE` | BOOT_MODE |
| `0xF1` | Upgrade MCT to resizable partitions |
| `0xF7`/`0xF8` | Write data |
| `0xEF 0x80` | Reboot |
