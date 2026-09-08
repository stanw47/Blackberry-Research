==============================================================================
SESSION 15 — OLEKSANDR UNLOCK CONFIRMED + BOOT0 BUILD PREP (2026-09-08)
==============================================================================
Result: oleksandr bits 42/43 set in NV record 0x2019, persisted, boot0 EROFS
still enforced by the running FS driver. imggen image generation proceeded
offline using live device dumps + official OS image. No flash performed.

------------------------------------------------------------------------------
[1] NV 0x2019 bits 42/43: SET + PERSISTED (on-device, libnvram API)
------------------------------------------------------------------------------
  - Used sanctioned libnvram.so.1 API (not /dev/nvram devctl):
      nv_get_record(0x2019, buf, 128) -> value 00 08 ... : SECURE/unrestricted
      nv_write_record(0x2019, buf | 0x0C at byte5)    -> rc=0
      read-back: 00 08 00 00 00 0C 00 00 ...          changed=True
  - After full device reboot (OS re-flashed nothing; just reboot):
      read-back BEFORE any write == 00 08 00 00 00 0C 00 00 ...  changed: False
      => the write SURVIVED reboot (bit-flag interpretation is byte5 LSBs 2&3).
  - BUT: post-reboot live test
        pwrite(/dev/emmc/boot0, 1 byte at 0)  => EROFS (OSError 30)
    The flag does NOT make the running FS/block layer writable. Conclusion:
    these bits gate the OFFICIAL UPDATER's write path (autoloader flashing
    SBL1), exactly as "unlock via official RIM updater" states. The OS-lane
    live `dd` to boot0 remains read-only; the reproduce vector is to run the
    modified (imggen) images through the official updater, not host-side /dev
    writes.

------------------------------------------------------------------------------
[2] imggen "user"-input recipe -> SOURCES CHOSEN (live vs official OS image)
------------------------------------------------------------------------------
  Passport boot0 parsed on-device (build info @ 0x2DEB0, found via
  "RIM BlackBerry Device"):
    version '..*.' ??            hwid 0x87002C0A (windermere EMEA; product
                                'wolverine', variant 'emea' per imggen/bb.py)
    field8(secure) 0??          builder 'ec_agent'  date 'Apr 10 2014'
    field18=0xFFBD8            (rev_table/mct anchors)
    mct_offset 0xFFC00         mct_size 0x400
    MCT magic 0x92BE564A v1.29 partitions (offset<<16 / size<<16):
      nvram 0x210000 (4032K) cal_work 0x600000 (28672K)
      cal_backup 0x4200000 (65536K)  (induction: bccs f20 tone (bbss.insecure))
    mbr: os 0x28200000 (512M), system .., user 0x50200000 (32G)
  -> ls of /dev/emmc on Passport (root):
      boot0 boot1 cal_work0 dmi0 nvram0 os0 os1 radio0 rpmb0 sd0 uda0 user0
      NO cal_backup0 / NO nvram-only partitions (nvram0=4128768B= 0x3F0000*16.
      Only NONHYS blockmgr =512 sector; user0/uda0 = DOS (see mct os_mbr))
  Sources chosen for each imggen "user" partition map entry (offset-0x200000):
      nvram     <- LIVE PASSORT dump  /tmp/opencode/passport_nvram0.dump
                  (4,128,768 B; includes the 0x2019 unlock we wrote)
      cal_work  <- LIVE PASSORT dump  /tmp/opencode/passport_cal_work.img
                  (29,360,128 B via /dev/emmc/cal_work0)
      cal_backup<- OS 10.3.0.3216 UFS  /home/.../passport...v2.0.4.ufs @0x4000000
                  (67,108,864 B; no cal_backup0 partition on device)
  Cross-check (sha of first bytes): nvram UXFS chunk vs live dump DIFF because
  live holds the modified 0x2019 + live calibration - that is EXPECTED and
  DESIRED (preserve breakthrough + current cal).

------------------------------------------------------------------------------
[3] STATE OF THE imggen/bb10mt PY2 PORT (DONE -> py3)
------------------------------------------------------------------------------
  - sb_py22: imggen is python2 only; ported build-info/MCT/GPT/rev-table + the
    generate_hwi / Android-boot & user partition assembly into a py3 script.
    unix updater chain uses bb10mt (qCFM block) to repackage boot0+new Android
    master boot image into a QCFM/.signed CARRYING the SBL1 (boot0) contents.
    The official RIM updater then applies it. (This is the oleksandr unlock
    "reproduce the official RIM updater flash" path; the new boot0 becomes
    ACTIVE for next boot.)
  - We are NOT yet sure the autoloader will re-sign / keep the SBL1; the oleksandr
    bits gate the UPDATER step.  So THIS proof step as-is:
      "Flash the oleksandr-unlocked device with an autoloader whose SBL1
       (boot0) = imggen output, and see if the updater WRITES it (unlock) or
       errors/keeps stock (signature must be re-sealed)."
  - The 38MB v2.1 (radio) has NO SBL1; boot0 bytes must be injected into the
    OS v2.0 container (which bb10mt `unpack`/`pack` can rebuild) OR into the
    autoloader's merged image.  Each step replicates what RIM ships when it
    updates SBL1.

------------------------------------------------------------------------------
[4] PASSED HELPER TOOLS
------------------------------------------------------------------------------
  run_post_reboot.py        - SSH login + re-upload python+stdlib+pathtrust
                              after reboot wiped /tmp (re-run every boot)
  (nvwrite.py)              - set/verify 0x2019 bits + boot0 write probe (readback
                              proved persistence; probe still EROFS)

==============================================================================
NEXT
  1. Port finishing: build the actual new boot0/user with py3 (needs the imggen
     'files/' tables), clamp pass black.  Because updater carries SBL1, the
     generic 'boot0' the updater writes may be bbss+stage2 style vs the SBL1
     we generate - MUST verify updater's SBL1 sector count (does it write the
     full 4M boot0 or just sbl1 1M?).
  2. Decide flash vehicle: (a) native QCFM w/ bb10mt pack (fast, reproducible),
     (b) full autoloader.exe rebuild (matches RIM autoloader, signed tail).
  3. Pre-flight on a SPARE Classic first (already: Classic differs SoC - do not
     flash Passport-class autoloader onto Classic).

==============================================================================
[5] UPDATE - IMAGES GENERATED + VALIDATED (this session, same day)
------------------------------------------------------------------------------
  img3gen.py (py3 port of imggen, Passport/8974 aware) run SUCCESSFULLY:
    input:  /tmp/opencode/passport_boot0.img (live boot0 dump)
            /tmp/opencode/syn_user/user_input.img (synthesized: nvram=live
              partition, cal_work=live /dev/emmc/cal_work0, cal_backup=UFS)
    output: /tmp/opencode/new_boot0.img  (3,896,320 B)  [fits 4MB boot0]
            /tmp/opencode/new_user.img   (411,041,792 B)
  VALIDATED new_boot0: GPT hdr LBA1, hwi ("product = wolverine"), stage1/2
    (QCOM D1DC4B84), stage3 ELF, bbss, sbl1r, tz/rpm/sdi ELF, abootr
    (05 00 00 03) - all within 0x3B7400 < 4MB.  new_user: payloads at
    0x10000(nvram, has unlocked 0x2019), 0x400000(cal_work), 0x4000000
    (cal_backup), 0x8000000(aboot), 0x8400000(sbl1), 0x8C/0x90(blog/prdid),
    0x14000000(modem); zero tail to system slot (flash-trimmable).
  NOTE: imggen boot_gpt first_lba are SECTORS; user_gpt first_lba are BYTES
    (RIM tool quirk) - handled correctly in img3gen.py.
  imggen files/ ARE 8974-class (aboot: target/msm8974, sbl1: ADC_BOOT_BSP_
    8974PRO_PMA8084) - images are Passport/STV100 (Windermere-class)
    compatible.  The boot0 chain is the Balika-verified Z30-style prototype;
    consumer-PBL fuse acceptance STILL UNPROVEN on this unit - first flash
    should be on a SPARE (AAW068 Passport-SE / STV100-1 / oslo) if available.
  FLASH VEHICLE still open: (a) bb10mt pack QCFM with injected SBL1, or
    (b) rebuild autoloader.exe tail.  NOT YET DONE.
==============================================================================
------------------------------------------------------------------------------
  UPDATE 2026-09-07 (session continued)
------------------------------------------------------------------------------
  DEVICE TOTALITY: Passport powered OFF + disconnected by user (waiting).
  IMPORTANT PROTOCOL CORRECTION (from user): the BB device does NOT present
    itself for flashing/reading on its own.  While powered OFF and plugged,
    it only CHARGES.  It only enters the flash/loader mode when a HOST TOOL
    is actively LISTENING/polling for the BlackBerry (0FCA) device.  So the
    correct order is:
        1. start the listening/polling tool on the PC FIRST
           (bblink.py / bb10mt probe loop),
        2. then connect the powered-off device to that PC's USB,
        3. only then does the device respond as BootROM (PID 0x0001)
           -> RAM-loader (PID 0x8001) and accept a flash session.

  ANALYSIS RESULTS (this session):
  - bb10mt autoloader internals (uautoloader.pas): MakeAutoloader = cap.exe
    stub (PE, GetPEEndOffset) + ver2 header (3x START_SIGNATURE_DWORD
    $97C5D59C, 80 bytes of zero dwords, count, 64-bit offset table) + the
    .signed files appended.  Pre-rooted Passport exe verified congruent
    (split gave v2.0.signed [ifs 10MB / rcfs / sig2 / mbr / ufs 2.6GB] and
    v2.1.signed [radio.rcfs / radio.sig2 / radio.mbr]; cap.exe 9.2MB).
    NO boot image in either container -> boot0 write does NOT ride the
    .signed OS-reload path.
  - bb10mt flash/ramloader flow (ramloader.pas): ConnectToBB reboots any
    non-BootROM product, connects PID 1, SetMode(1), PasswordInfo,
    SwitchChannel, LoadLoader(modelID via IDtoADDR, $2C0A->$0DD00000),
    SendAndRunLoader, WaitForLoaderMode($8001), InitializeLoaderInterface
    (SetMode(2), PasswordInfo, BugdispLog, FlashRegionsInfo).  FlashFile:
    PreFlash($40 for 2C0A / $15 else), F7 SendBlock chunks (4-byte block#
    + 4-byte size + data, <= 0x3FF4), then SendSignature($40F9) with a
    560-byte DUMMY (all-zero) signature, Complete($40C0).  NOTE: dummy
    signature likely why bb10mt-only flashes were rejected/never stuck.
  - QCFM (qcfm.pas Ext2Type): the container entry TYPE is chosen by the
    file extension (.nvram/.ufs/.mbr/.sig/.ifs/.rcfs/.radio.*/.sig2/.calwork/
    .calbackup/.dmi/.os/.dmi.*).  NO type maps to boot0/boot1 -> the loader
    routes streams to OS/user/radio regions only; boot0 region (MCT kind
    $2B "Boot0 MMC", mct.pas:55) has NO container entry type.  Hence a
    boot0 write cannot be carried by bb10mt FlashFile / a .signed image;
    it must be the loader's raw boot-region write op (SBL-flash / the
    SDCC special-vendor-cmd path, cf. loader_04002E0A-00.bin strings).
  - On-device update machinery found (dev build, rooted):
    - /proc/boot/hold_boot [ELF, name_open+MsgSend] + start_hold_boot.sh
      run '/proc/boot/hold_boot -vvvv'  -> OS entry into loader-hold
      ("Reload OS") state WITHOUT power-cycling.  exit 99 = bad battery,
      sets 'nvram_bits set boot_profile 1' (backup boot mode).
    - /base/bin/__upd,u_upd,g_upd,__cgi_update,__appupdatenotifier =
      OTA/update engine (the real updater eventually re-enters the SAME
      RAM-loader path; no unsigned-injection hole found).
    - blupdater (/sbin, 3496B) is an ARM ELF = oleksandr root-install
      wrapper (runs /accounts/devuser/rootdata/install.sh) - NOT a boot
      updater.  Dead end.
    - os_device_image_check reads /proc/boot/os_boot_lock_devices.txt
      (EMPTY on this build) -> the "image incompatible with board" gate
      never trips.  Dev-build relaxation applies to OS-start sanity only,
      NOT the PBL->SBL trust chain / boot0 signature enforcement.
    - powerauth, qcomload: battery auth / QC CSM load - not flash paths.
  - IDtoADDR(PASS 0x2C0A) = 0x0DD00000 (RAM-loader load address).
    MAX_FLASH_BLOCK=$3FF4.  WaitForLoaderMode polls USB product $8001.
  - MCT kind enum: ekBoot0=$2B (Boot0 MMC), ekUser=$31, ekBootrom=$18,
    ekMCT=$32, ekOSNV=$1E, ekCalWorking=$37, ekOSExt=$3B, ekCalBackup=$38,
    ekMBR=$34, ekOSFixed=$1B, ekRadioFixed=$3A, ekFSFixed=$1C, ekQNXRegion
    =$35, ekPartition=$39.  (mct.pas)
  - PASS USB enumerates as 0FCA: PID_BOOTROM=0x0001, PID_RAMLOADER=0x8001,
    PID OS-mode=0x8017 (bblink.py).  RNDIS/SSH channel is the OS-mode
    bridge; raw USB flash access requires libusb on the attach host.

  NEXT (pending device reconnect):
    1. Verify NV bits still 0x0C (quick) - optional once OS channel up.
    2. START LISTENER FIRST on this Linux box (bblink.py probe/connect or
       bb10mt), THEN user connects the POWERED-OFF Passport to THIS box's
       USB.  Device responds in BootROM (0x0001) -> RAM-loader (0x8001).
    3. READ-ONLY loader session: GetMCT (cmd $D9) -> extract Boot0 entry
       (range + flags) + FlashRegionsInfo; NO F7 writes; then clean
       Reboot($80EF).  This maps the live boot0 region needed to craft
       the boot0-targeted F7 stream.
    4. Craft + run the boot0 write (new_boot0.img) then user (new_user.img)
       if/when user approves; verify read-back; then boot Android chain.
  HOLD: bblink.py connect() auto-reboots a live OS phone; it must only be
    invoked with the device OFF (listener-first per correction above).
  WIP LOCATIONS: /home/stanw47/priv-research/working/shroot/ (rooted exe
    split: v2.0.signed, v2.1.signed, cap.exe); /tmp/opencode/loaders_x/
    pp_cap/ (RAM-loaders); /home/stanw47/priv-research/working/ (images,
    dumps moved off the small /tmp).  /tmp/opencode had OOM (3.9G tmpfs)
    - big artifacts live in /home/stanw47/priv-research/working/.

==============================================================================
[6] UPDATE - PASSPORT LOADER LANE BUILT (READ-ONLY) + LIVE LISTENER RUNNING
------------------------------------------------------------------------------
  Loader selection (imggen/dev-build only - do NOT mix): the RAM-loader is
  passed via `--loader` GLOBAL arg BEFORE the subcommand (argparse).  For the
  Passport the correct loader is:
      /tmp/opencode/loaders_x/pp_cap/loader_8D002C0A-00.bin
      (222,624 B; IDtoADDR(0x2C0A) = load addr 0x0DD00000)
  loader_04002E0A-00.bin is the WRONG class (loads at 0x80200000) - rejected.
  load_loader checks: magic @ offset 4 == 0xD7D32D1F, footer @ -8 ==
  0xD7C82D1F.

  bblink.py `info` now saves the FULL MCT blob: `info --loader ... -o/--out
  FILE` (+ `--keep` clean-reboots the loader after the read).  Added
  BBSession.session_reboot() (Channel0 cmd 3) used to drop an OS-session PID
  0x8017 device back to BootROM.

  tools/listen_flash.py = listener loop: probes every ~1s; on BootROM/RAM-loader
  PID runs ONE read-only `info --out /tmp/opencode/mct_raw.bin --keep`
  (cread/GetMCT only - NO F7/F8 writes).  First live observation: with the
  listener running and the Passport plugged, the device was seen as OS-mode
  PID 0x8017 (booted to OS), not BootROM 0x0001.  So the powered-off->plug
  ritual must be repeated while the listener is alive; a device that is merely
  plugged while already booted will just enumerate as the OS session.

  NEXT (device currently sits in OS mode PID 0x8017 per the listener log):
    1. Power the Passport OFF fully; keep listen_flash.py running.
    2. Plug it in -> expect BootROM PID 0x0001 -> RAM-loader PID 0x8001.
    3. Listener auto-runs read-only info -> MCT blob -> /tmp/opencode/
       mct_raw.bin.  Parse Boot0 MCT entry (kind $2B) + FlashRegionsInfo.
    4. Craft the boot0-targeted F7 stream from that map; flash new_boot0.img
       then new_user.img on user approval; verify read-back.
  NOTE: MCT capture is still pending (device never reached BootROM yet this
  session - it keeps booting to OS).  Do NOT resume EDL-style handshakes from
  OS mode; offline analysis continues in /home/stanw47/priv-research/working/.
