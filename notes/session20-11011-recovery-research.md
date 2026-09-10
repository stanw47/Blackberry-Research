# session20 - 11011 "Flash Erase Failure" decode + recovery research (Passport)

## Status: Passport stuck in BootROM error 11011; USB not enumerating

- Device blinks `11011` (blink-blink-pause-blink-blink) permanently since a button
  combo; will not change. Not on the local bus (`lsusb` shows no 0FCA device).
  Background listener (listen_flash.py --armed, PID 231145) polls continuously.
- Windows autoloaders (pre-rooted v2, stock, Android-modified) that previously
  worked now fail ~13% at "Signature Trailer" -> "Flash Operation Failure".
- README front page rewritten for readability and pushed (7453eca). boot0/boot1
  integrity re-verified from dumps this session (see [3]).

## [0] THE DECODE: 11011 = "Flash Erase Failure"

Confirmed independently on TWO vendor tables (both derived from RIM BootROM
error-blink codes):
  - chimeratool.com/docs/blackberry-bootrom-error-blink-codes
  - furiousgold.com/en/help/blackberry-bootrom-error-blink-codes

Reading: "1" = LED blink, "0" = pause. The code is emitted by BootROM when it
cannot complete a flash-erase operation. 11011 is a palindrome, so MSB/LSB read
order does not change the value.

Complete table of interest:
  Code     Description                    Vendor diagnosis
  11       No OS Loaded
  101      Bad OS CRC
  1011     Missing OS Trailer
  1101     OS Not Signed
  1111     OS Signature Invalid
  10101    Unknown Flash Manufacturer
  10111    Flash Initialization Problem
  11011    FLASH ERASE FAILURE   <- we are here
  101011   USB Driver Error
  101101   No Bootrom CRC
  101111   Flash Write Failure
  1011111  General Assert Failure
  1011101  NAND failure
  (continuous) = security wipe in progress OR broken hardware (NOT bootrom err)

Earlier reported "101111111" (9 bits) during the 20 flash attempts is not a
table code; nearest interpretations by length:
  - 101111 (6 bits) = Flash Write Failure  <-- matches the writing-era behavior
  - 1011111 (7 bits) = General Assert Failure
Red-LED bursts are easy to miscount; the 11011 now shown is unambiguous.

## [1] Why the erase now FAILS (root-cause hypothesis, strengthened)

Sequence that leads to this state:

1. session14: incomplete BootROM password exchange -> BootROM/SBL orders a full
   SECURITY WIPE. Wipe re-runs whenever the USB host drops/errors (observed
   twice). This is the "Reload OS" loader state.
2. session15: NVOSSTORE 0x2019 byte5 = 0x0C persisted (bits 42/43 = "boot
   partition write allowed" per oleksandr unlock method). Tells the official
   updater that SBL1/boot0 MUST be written during flash.
3. session18: armed NV WP=1 / WP_PROGRESS=1; re-read EXT_CSD -> BOOT_WP[173]
   = 0x04 (bit2 B_PERM_WP_EN) both before AND after clean power cycle.
   Boot0 is PERMANENTLY write-protected AT THE CARD. Software cannot clear it.

Result:
- The wipe's erase pass covers the boot region; the card refuses the erase on
  the fused-WP boot partition -> BootROM reports **11011 Flash Erase Failure**
  and cannot advance to load any OS.
- Independently, the official updater (driven by the 0x2019 bit-42/43 pose)
  attempts the SBL1/boot0 write path -> card rejects -> autoloader aborts at
  "Signature Trailer" ~13%.

This also explains why everything worked BEFORE the session15 NV poke and now
consistently fails: prior to the NV change the official updater skipped boot0
writes (card WP invisible to it); after it, the updater must write boot0 and
collides with the card-level fuse.

## [2] PROBED-STATE INTEGRITY (boot0/boot1 were NOT corrupted by poking)

Verified from dumps left in this repo (dumps/passport/):
- bb0_full.bin: EFI GPT "EFI PART" @0x200; ELF magic @0x4f9e8/0x56e41/0x757e9;
  SBL1 strings present; structurally intact.
- bb1_full.bin: all-zero (stock blank for this unit).
- Every boot-partition write attempt in sessions 15/17/19 was refused EROFS/EIO.
  Nothing ever landed on boot0/boot1. Corrosion/physical-flash damage is ruled
  out as the cause of 11011; the erase failure is policy (WP), not hardware.

## [3] RECOVERY LADDER (least to most invasive)

1. HARD RESET the loop: Passport battery is NON-removable, but hold
   Volume-Up + Volume-Down + Power together for ~32-40s (documented reset on
   BB10/CrackBerry). This does not clear permanent WP but may exit the 11011
   latch and bring the device back to an enumerating reloadable state. Leave it
   charging; low battery aborts erases.
2. THE MOMENT IT ENUMERATES, act in one shot: keep listen_flash.py --armed
   running so BootROM (PID 0x0001, model_id 87002C0A) is caught as it powers
   up, then immediately run the pre-rooted v2 autoloader (Passport
   10.3.03.3216 root_v2). v2 embeds mod_nvram (-u unlock / -d downgrade) and
   backs up NVRAM, which is exactly the lever that can reset the 0x2019 bits
   that are pulling the updater into the boot0-write path.
3. If it reaches the OS again: run nvram_bits.py to clear 0x2019 byte5 0x0C->
   0x00 and NV WP/WP_PROGRESS (nvram0 record 0x2019 -> offset 0x100C80), reboot,
   then re-flash the STOCK autoloader (updater goes back to skipping boot0).
4. If it stays 11011 / never enumerates: the only remaining lane is HARDWARE -
   ISP/desolder direct eMMC access (UFI/EasyJTAG class tool). This is also the
   only path that can clear the card-level BOOT_WP[173]=0x04 permanent fuse or
   rewrite the boot block out from under it (the balika011/imggen route). No
   software path exists past a fused permanent WP + erase-on-wipe combo.

## [4] Open items / risks
- Whether the 11011 latch persists until the battery is fully drained, or a
  32-40s reset truly re-enters the loader (the 0010 "Reload OS" loader speaks
  official-updater protocol only and ignores bb10mt channel0 - cannot be driven
  by bblink tools).
- Risk of re-triggering the wipe-loop on attempted handshakes is LOW now only
  because the device doesn't enumerate; when it returns, every USB host drop
  re-arms the wipe. Keep sessions short (one autoloader run per power-up).
- 0x2019 bit-42/43 endianness/flag-base remains the softest link; mod_nvram's
  real behavior on this unit is the cheapest way to re-derive it.

## References
- chimeratool.com/docs/blackberry-bootrom-error-blink-codes
- furiousgold.com/en/help/blackberry-bootrom-error-blink-codes
- bb10.root.sx blog: Pre-rooted autoloaders v2/v3 (mod_nvram, NVRAM backup,
  term49, root architecture) - also credits stanw47 for system-wide root.
- notes/session14/15/18 within this repo (wipe-on-failed-handshake, 0x2019
  pose, permanent BOOT_WP).