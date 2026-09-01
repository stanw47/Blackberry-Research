# Priv AAW068 aboot — Session 3: FULL auth-boot code decoded (ARM mode)

Start addr refs: LOAD seg off 0x8000 -> va 0xf900000, filesz 0x1634bc
disassembled with capstone CS_MODE_ARM (NOT thumb!). All addresses = virtual.

## 1. Caller chain
- Loader entry (big, at 0xf92d5d4) loads boot region: "Loading boot image (%d): start" (0xf92d8d4) / done (0xf92d97c).
- Calls auth gate: 0xf92d9d0 `bl 0xf94d464`  (r0=handle, r1=struct, r2=size)
- `cmp r0,#0; bne 0xf92da00` -> nonzero = AUTH OK -> continue boot (0xf92da00).
- zero = FAIL -> prints "Authenticating boot image failed!" (0xf92d9dc).
  -> `bl 0xf94ca14` (factory/blocklist check): if result==0 print "Device is in factory mode continuing..." and CONTINUE BOOT ANYWAY.
  -> else if result==2 specific path -> 0xf92dde8 NV-fatal. else abort.
- Factory mode source: RPMB field "BOOT_MODE_TYPE" == "FACTORY_MODE" (read via f96a0c8/f969fa0 RPMB API)
  => 0xf94c928 sets [0xfa525e8], f94ca14 returns 0=none /1/factory.

## 2. auth dispatcher 0xf94d464
- reads magic at [r1]: compares to 0xef50b41 (LE bytes 41 0b f5 0e = "APBI" file magic w/ our sigs).
- magic MATCH  -> token/cert path (below).
- magic MISS   -> `bl 0xf94e094` (insecure-check). If returns 0:
      print "Ignoring auth failure on insecure device" (0xf9d4468) -> return r0=1 = SUCCESS, boot despite bad/absent sig!
   else `bl 0xf93dd38` (debug-token load). If returns nonzero:
      print "Debug token hlos_unsigned is active. Skipping image verification" (0xf9d4494) -> return 1 = SUCCESS.
   else return error 0x41.

## 3. Signed-image path (magic found)
- Iterates 4-entry key table at 0xf9d42ac (entries 8 bytes: keyname*, keydata*):
     0xf9d43a4:"ABDI" -> 0xf9d44e8
     0xf9d43ac:"ABBI" -> 0xf9d45f8
     0xf9d4328:"APBI" -> 0xf9d4570
     0xf9d44e0:"ACBI" -> 0xf9d4680
  uses strcmp (f971bcc) to match the image's advertised key id; picks matching cert data.
- Then `bl 0xf94d378` = the real verify routine:
   h = hashclone init (f9bee78), update(image r1*r2), update(0x48 bytes struct), finalize(f9bef4c)
   -> f966a84(hash, cert, sig) checks sig-block header byte in {2,3,4} w/ key 0xf9f6268
   -> f96696c = ECDSA instead? Actually returns 1 on success (verified) -> caller r5=1.
- So signature verify uses ECDSA public keys EMBEDDED in aboot?? or hash-compare.
- (f96696c: builds hs/digest via f9678ac/f967330/f965f9c... calls f965be8 / f967018.)

## 4. The insecure flag [0xfa525f0+0x18] (addr 0xfa52608)
- SET by parser 0xf94d818: reads device-info (f904258 idx 0x87 "BBSS"), then
  loads string field "bbss_insecure" (0xf9cb6b0) and if value=="true" (0xf9d4edc)
  => [0xfa52608] = 1  (insecure). Also parses bbss_wp_type / bsis_type etc.
- READ by 0xf94e094: returns 1-[flag]; used at (a) auth MISS path above, (b) boot-anyways check 0xf92dcf8 -> "%s : (insecure) continue boot".

## 5. Token files (debug mechanisms) - all under /nvuser or /perm, NOT flashable ungated:
   /nvuser/hlos_unsigned.tkn  state=development -> skip image verification
   /nvuser/dbg_console.tkn    loglevel=...
   /nvuser/sw_rollback.tkn    disable
   /nvuser/pathtrust_mode.tkn ...
   /nvuser/selinux_mode.tkn   policy permissive|enforcing
   /nvuser/mfg_mode.tkn       counter
   /perm/ddt.tkn, /nvuser/ddt.tkn

## 6. Unlock mode
- "Device is unlocked! Skipping verification..." (0xf9ce010) - printed in another branch (bootlinux), from devinfo is_unlocked. gated write (devinfo denied).

## Takeaway
- No EDL. No way to forge ECDSA without key.
- Three runtime flags can each allow unsigned boot IF we can set them:
   a) [0xfa52608] insecure (set from BBSS "true") - comes from TZ-ish blob, not flashable.
   b) debug token /nvuser/hlos_unsigned.tkn state=development - nvuser partition flash denied.
   c) bootmode FACTORY_MODE in RPMB - RPMB needs key.
- => All three look gated by TZ/fusion from aboot fastboot. Remaining hope:
   exploit a parser bug in the sig header handling (f966a84 block-length logic,
   f94d464 key-id strcmp, length field), OR find writable-direct-IO path (mmc raw
   writes gated), OR downgrade/rollback to a bootchain with weaker code.
## 7. SEMI-FINAL: full permission model + the real gate (session 4)
- Command registration: each command is a node in linked list [0xfa7419c]; dispatcher 0xf924498
  matches name via strcmp, then calls gate 0xf9354d4. If gate != 1 -> "user does not have
  permission to run command %s" (0xf9c93f4) / FAIL. 
- Permission table at 0xf9d1774: entries (name, type_id). lookup 0xf93513c/0xf9351f4.
  type in {0..10} jump table at 0xf93521c.
    type 0: no auth needed  (getvar:, reboot, reboot-bootloader, continue, boot,
                             oem securewipe, oem enable-usb-shutdown, oem info)
    type 1: f93e8bc()==? then usually allowed (flash:, erase:, download:,
                             oem enable-usb-reset, oem led:, oem erase-ddr-training-primary/backup,
                             oem set-product-mode)
    type 2..10: movw r1,#0x1000..0x1008; ldr r0,[0xfa7cbf0]; bl 0xf935098 (rtas auth check)
                             -> needs authboot channel opened. (all others: getvarp, blocklist-wipe,
                                gptinfo, format, test-ddr, clear-anti-theft, set-factory-mode, mmcinfo,
                                read, dmesg, mmchealth, clear-lal, grswipe, bootlog, ddrinfo, bootmetrics,
                                charger-screen, console ...)
- f935098: uses ctx[0xfa7cbf0] (authboot ctx), checks work-level [ctx.work]+0x170*idx+0x70 == 6
  -> else "rtas_cmd_authorization_check failed" (0xf9d164c). String "AUTHBOOT" partition at 0xf9d16a8.
- So: `oem set-product-mode` (type 1) is UNPRIVILEGED and WRITES RPMB BOOT_MODE_TYPE=PRODUCT_MODE.
      `oem set-factory-mode` (type 6 / cmd 0x1005) REQUIRES AUTHBOOT. Confirmed live:
      product-mode: SUCCESS; factory-mode: "authboot command permission denied".
- fastboot `boot` / RAM boot: NOT IMPLEMENTED - "Not supported" (0xf9cdc90, used at 0xf92c970). 
  No fastboot-boot unsigned path.
- First-boot init: 0xf94d240 (3rd caller of mode-writer f94ccbc) sets bootmode once from a fuse;
  reads fuse (f94d1b8, key 0xfc4b81f8 = qfprom/row), if bit 0x2000000 not set: pick mode from
  "rome" product compare (0xf9d41fc) -> f94ccbc(r6,1) -> burn fuse via f94cfcc. On already-initialized
  device this path is inert.
- "Device is unlocked! Skipping verification..." (0xf9ce010) & "Keystore verification failed!
  Continuing anyways..." (0xf9ce040) are DEAD STRINGS in BOTH AAW068 and STV100-1 aboot
  (no movw/movt/ldr-pc/adr xrefs). No unlocked-bypass code path exists.

## Bottom line (what blocks us)
- Boot-image verify = in-aboot ECDSA P-256 with 4 embedded keys; no private key -> cannot forge.
- All software bypasses require either: TZ-signed BBSS data (bbss_insecure), an authboot-authenticated
  fastboot session (factory mode switch), or write access to /nvuser (debug token) / RPMB via the 
  gated oem set-factory-mode. None are reachable from unauthenticated fastboot.
- Only unprivileged oem*: info, securewipe, led, erase-ddr-training-*, enable-usb-reset/shutdown,
  set-product-mode (already the default state). set-factory-mode = auth-gated.

## 8. FINAL attempt: debug token / nvuser (session 4 cont.)
- `fastboot boot` (RAM boot) = NOT IMPLEMENTED. Stub returns "Not supported" (0xf9cdc90 used at 0xf92c970).
  No fastboot-RAM-boot unsigned path. Verified live: "downloading... OKAY, booting... FAILED (remote: Not supported)".
- Two auth-fail overrides exist in verify dispatcher 0xf94d464:
  1) insecure device: 0xf94e094 reads [0xfa525f0+0x18] (int, set to 1 when BBSS config value
     "bbss_insecure" == "true" (0xf9d4edc)) and [0xfa525f0+0x1c] (byte; 0=prod,1?,2=OEM-unlock).
     Set only in 0xf94d860 from BBSS partition config (f935880 reads nv config). NOT settable
     from fastboot; flash of bbss/devcfg-type partitions denied; BBSS config is TZ-signed NV.
  2) debug token: 0xf93dd38 reads file "/nvuser/hlos_unsigned.tkn" (buf r5), parses header,
     compares 'state' field == "development" (0xf9d2d3c) -> returns nonzero => f94d574 prints
     "Debug token hlos_unsigned is active. Skipping image verification failure." (0xf9d4494)
     and auth failure is IGNORED (returns success, boot continues).
  OTHER token files in aboot: /nvuser/dbg_console.tkn, /nvuser/sw_rollback.tkn,
      /nvuser/pathtrust_mode.tkn, /nvuser/selinux_mode.tkn, /nvuser/perf_config.tkn,
      /nvuser/ddt.tkn, /nvuser/adb_mode.tkn, /nvuser/mfg_mode.tkn, /nvuser/power_mode.tkn,
      /nvuser/mode.tkn, /nvuser/system_dbg.tkn. getvar exposes state:
      "hlos_unsigned.tkn:disabled", "hlos-signature.tkn:NONE", "is-password-set:no",
      "security:enabled", "bootmode:PRODUCT_MODE".
- CRITICAL: nvuser is NOT a fastboot-flashable partition. `getvar partition-type:nvuser`,
  `efs`, `bbss`, `frp` all return EMPTY. Only flashable: system/userdata/cache/oem/carrier
  (ext4) + boot/recovery/sbl1/aboot etc whatever gptinfo lists. nvuser lives on a keyed/
  structured partition (RPMB-adjacent, "nvuser" @0xfa3d620 near "metadata" @0xfa3d608,
  RPMB record helpers rpmb_read_record/rpmb_find_record/rpmb_block_read/write at 0xfa3ca18+).
  Writing /nvuser/*.tkn requires the authenticated NV channel (not available).
- Led type-1 cmd (0xf935684) is only strncmp dispatch on fixed colors, no format string.
- getvarp:/read:/dmesg:/format/gptinfo/blocklist-wipe all authboot-gated.
- oem getvar "swipelock=bootloader" etc not present; no oem unlock command at all.
  (Table has no unlock/carrier-unlock entry; only the ones dumped in section 3.)

## FINAL VERDICT (session 4)
- No software-only bypass exists from unauthenticated fastboot on AAW068 aboot:
  * factory mode  (RPMB BOOT_MODE_TYPE=FACTORY)  -> oem set-factory-mode => AUTHBOOT gated (type 6)
  * debug token   (/nvuser/hlos_unsigned.tkn state=development) -> nvuser not writable from fastboot/RPMB
  * insecure flag (bbss_insecure=="true" in BBSS) -> TZ-signed NV config, flash denied
  * "unlocked/devboot" skip -> strings dead code in both AAW068 and STV100-1
  * RAM boot `fastboot boot` -> not implemented ("Not supported")
  * forging boot/recovery sig -> needs BB private key (4 embedded keys ABDI/ABBI/APBI/ACBI)
- Untried (requires hardware or signed material): JTAG/EDL (none), fuse blow via qfprom (needs TZ/permission),
  obtaining a valid RIM debug token, or an authenticator that has authboot (RIM factory tools only).

## What WOULD work (for completeness)
- An official RIM "unlocked" autoloader / token (not public) could write a valid hlos_unsigned.tkn
  or bbss_insecure=true, or authboot-open factory mode. No public one exists for STV100-1.

## 9. Ghidra toolchain verified (session 4)
- ghidra 12.0.4 (DEV) at /usr/share/ghidra, Java 25. Headless import of emmc_appsboot.mbn
  as ARM:LE:32:v8 / BinaryLoader, then rebase to image base 0xf8f8000 (file off 0x8000 -> 0xf900000).
  Commands:
    analyzeHeadless /tmp/ghidra_proj bbry -import <mbn> -processor ARM:LE:32:v8 -loader BinaryLoader
    analyzeHeadless /tmp/ghidra_proj bbry -process emmc_appsboot.mbn -noanalysis \
        -scriptPath /tmp/ghidra_py -postScript DecompileKey.java
  (scripts in /tmp/ghidra_py; must import ghidra.program.model.address.Address or compile fails)
- DECOMPILED CONFIRMATION of permission gate FUN_0f9351f4:
    type 0  -> allow
    type 1  -> FUN_0f93e8bc()==0 ? allow : authboot(0x1000)   [BBSS sec-config state]
    type 2..10 -> authboot(0x1000 + (type-2))
  FUN_0f935098: ctx != NULL && *(char*)(*ctx*0x170 + 0xfa79978)=='\x06' -> rtas 0xf954858
                else "authboot channel not opened" (0xf9d1190) -> deny
  FUN_0f93513c: linear scan of table at 0xf9d1774 (35 entries), string match cmd name.
- VERIFY dispatcher FUN_0f94d464 decompiled: after ECDSA fail, only two overrides:
    FUN_0f94e094()==0  -> "Ignoring auth failure on insecure device"  (BBSS bbss_insecure)
    FUN_0f93dd38()!=0  -> "Debug token hlos_unsigned is active"        (/nvuser/hlos_unsigned.tkn)
  No other escape. Both require data we cannot write from unauthenticated fastboot.
- Note: flash/erase/download are type-1 = effectively unprivileged WHILE BBSS sec state keeps
  FUN_0f93e8bc()==0; live device confirmed this (set-product-mode succeeded). The image-content
  signature gate is separate (bootloader.cmd_flash* -> verify dispatcher), so flashing signed
  images works, unsigned never.

## Session 4 addendum — dispatch loop + full command table + handler verification

### Fastboot dispatch loop FUN_0f924490 (definitive)
- Reads 0x40-byte command via `(*pcRam0fa741c0)(buf,0x40)` (DWC3 read).
- Iterates registered command list `puRam0fa7419c`; prefix-matches name (len stored at node[2], handler at node[3]).
- For each match: `FUN_0f9354d4(cmd,len)` → if ==1 call `handler(cmd+namelen, dlbuf, dlsize)`; else "user_does_not_have_permission" + "authboot_command_permission_denied".
- getvar-all branch in FUN_0f924990: 64B stack buf, strncpy(name,0x40)+": "+strncat(value,0x40). Values are internal fixed strings (version/product/rtas keys base64ed) — NOT attacker lengths; bounded 0x40 per op into 0x40 buf → safe-ish (names/values internal).

### Static command table @0xf9cdc30 (name,handler) 16B stride
flash:→0xf92fdec, erase:→0xf92f2c8, boot→0xf92c948("Not supported"), reboot→0xf92c9c8,
reboot-bootloader→0xf92ca1c, oem unlock→0xf92edec, oem lock→0xf92ee50, oem verified→0xf92eeb4,
oem device-info→0xf92ca74, preflash→0xf92c988, oem select-display-panel→0xf92ed70.
- boot = "Not supported" (no RAM-boot path). Confirmed.
- oem unlock/lock/verified only toggle RAM flag 0xfa512f8 (+FUN_0f92ed0c persists via... live-denied anyway: NOT in whitelist → dispatch denies).

### Whitelist @0xf9d1774 does NOT list: oem unlock/lock/verified/device-info/preflash/select-display-panel
→ these commands are DENIED at dispatch (no entry → FUN_0f9351f4 default → 0). Confirms live "authboot permission denied".

### Flash gate FUN_0f92fdec (verified, /tmp/ghidra_flashfull.txt)
- Step 1: FUN_0f935380() (factory gate). If !=1 → "user does not have permission to flash" + "authboot_flash_permission_denied", NO image processing. → **flash: is DENIED on product-mode device even though dispatch type=1.**
- Step 2 (only when factory mode or authboot gate passes): `*param_2 == 0xED26FF3A` sparse parsing (0xcac1..0xcac4 chunk types w/ bounds checks) or raw ANDROID! boot-image write w/ size checks. → In-handler no signature verify of boot/recovery images; boot-time verify catches unsigned later.

### Erase gate FUN_0f92f2c8 — same pattern (FUN_0f935380 gate, then per-partition erase; tokens/phyboot0/1/vtnvfs handling). DENIED unpriv on product mode.

### Download path FUN_0f9246bc (/tmp/ghidra_fb.txt)
- hex size parse → `if (uRam0fa741d8 < uVar4)` reject "data too large". Then "OKAY" + usb_read into 0x10100000 buffer (uRam0fa741e4). size-capped. No overflow.

### DWC3 active (MSM8994): FUN_0f900ba4 returns "dwc" (0xf9c1d14) default → Set A ptrs:
0xf9203f0(alloc),0xf91fd60,0xf91fe2c,0xf920698,0xf9203f0,0xf9205c0,0xf920660,0xf923fe0(read),0xf923e58(write).
- FUN_0f923fe0 USB read: chunked ≤16MB per queue, len=param_2 exact → writes param_2 bytes to buf. size-safe w/ dl cap.

### oem getvarp:/read: helpers (0xf92b068/0xf928c7c) — authboot type2/8 gated at dispatch; internal parsers use 64-char bounds. NOT unpriv reachable.

### erase-ddr-training-primary FUN_0f9251ec — partition erase of 0xf9cabf4; no input parse. Safe.
### All remaining unpriv handlers verified clean: securewipe(wipe flag), grswipe, info(FUN_0f93532c), enable-usb-reset/shutdown(flag), set-product-mode(FUN_0f94ccbc(1,0)=RPMB PRODUCT write → no-op in product; caused no unlock), led(color strcmp).

### VERDICT (session 4)
Dispatch gate + handler inner-gate verified end-to-end at source level. NO unpriv fastboot command can:
1. set FACTORY mode (only oem set-factory-mode type6 → 0x1004 authboot; first-boot init pre-fuse),
2. free-flash boot/recovery (flash:) without factory mode or authboot,
3. RAM-boot (boot unsupported),
4. seed the work-level byte 0xfa79978 to 0x06 (authboot ctx channel).
No memory-corruption primitive found in any type-0/type-1 handler (all bounded/fixed-size). Fastboot attack surface: CLOSED.

## Session 4 addendum (EDL/firehose + live whitelist confirmation)
- EDL/reboot magic in aboot: `FUN_0f901004(magic)` writes `param_1` to reboot-reason word at `0xfe80f65c` (0xfe87f65c if DDR-prefill), then `FUN_0f900fb4(mode)` ORs mode into PMIC reg 0x88e. Modes: `0x77665500`->0x10, `0x77665502`->0x8 (dl), else 0xa. Secret reg write happens via FUN_0f96ff9c. No fastboot command calls with 0x77665502 -> no `reboot edl` path from aboot.
- SBL1 (sbl1_signed.mbn, non-ELF custom wrap) contains full EDL path: `usb: going for EDL`, `dload mode, skip rpm` -> EDL reachable at SBL level (key combo / PBL), but no way to trigger it from aboot fastboot.
- No firehose programmer (prog_emmc_firehose_8994_ddr.elf) in either autoloader; EDL flashing still needs signed programmer.
- Whitelist @0xf9d1774 (35 entries, stride: {name_ptr,type,0,flag}): types 0 free, 1 gated by FUN_0f93e8bc() (RTAS query), 2-10 map to RTAS mux codes 0x1000-0x1008 checked via FUN_0f935098 (0xfa79978 table). Per-partition flash gate: FUN_0f935380 (erase) / FUN_0f935380 (flash) look up partition in table @0xf9d12cc (56 entries: pmic,hyp,sdi,aboot,sbl1,rpm,tz,system,modem,boot,bootsig,recovery,...,nvuser).
- oem subcommands: no re-auth check in sub-dispatcher FUN_0f92430c; auth checked once at top dispatch level.
- LIVE CONFIRMATION (device serial 1161797525, fastboot, PRODUCT_MODE):
  - getvar all: bootmode=PRODUCT_MODE, authboot_api_ver=1.3, hlos_unsigned.tkn=disabled, hlos_signature.tkn=NONE, product=MSM8994, variant=na, subvariant=(empty), is-password-set=no, max-download-size=0x20000000.
  - type 0 allowed: oem info, getvar:, oem securewipe (untested), continue, boot (md only).
  - type 1 allowed: oem enable-usb-reset (OKAY), oem enable-usb-shutdown (type 0 btw), **oem set-product-mode -> SUCCESS, wrote RPMB, rebooted to fastboot, still PRODUCT_MODE**. flash:/erase: dispatch passes (type 1) but then fail the per-partition factory gate FUN_0f935380 in product mode.
  - type 2 blocked: oem getvarp: -> authboot command permission denied.
  - type 6 blocked: **oem set-factory-mode -> authboot command permission denied** (the ONE command that would flip us to factory).
  - type 8 blocked: oem mmcinfo.
  - Not in whitelist: oem device-info -> authboot command permission denied.
- Conclusion: whitelist is authoritative and enforced; no unpriv command can raise authboot level or set factory mode; EDL requires SBL key combo + we lack signed firehose. Fastboot attack surface confirmed closed at runtime, matching the static analysis.
