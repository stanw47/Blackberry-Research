#!/bin/python2

import sys, os, pkgutil, utils, bb, gpt, mct

if not len(sys.argv) == 5:
	print 'usage:', sys.argv[0], '<input boot0> <input user> <output boot0> <output user>'
	sys.exit(0)

print 'Finding build info...'
bb10_boot = utils.read_file(sys.argv[1])
build_info_offset = bb10_boot.find("RIM BlackBerry Device") - 0x10
build_info = bb.parse_build_info(bb10_boot[build_info_offset:build_info_offset + 0x4fc])

product = bb.hwid_to_product(build_info['hwid'])
variant = bb.hwid_to_variant(build_info['hwid'])
secure = build_info['secure']

print 'Parsing reversion info...'
rev_table =  bb.parse_rev_table(utils.buffer_read(bb10_boot, build_info['rev_table_offset'], build_info['rev_table_size']))
pcb_rev = rev_table['pcb_rev']
pop_rev = rev_table['pop_rev']
real_rev = pcb_rev
if product == "wolverine":
	real_rev = bb.wolverine_pcb_rev_to_real_rev(variant, pcb_rev)

print '\tproduct:', product, '(' + utils.hex(build_info['hwid']) + ')'
print '\tvariant:', variant
print '\tsecure:', secure
print '\tpcb_rev:', pcb_rev
print '\tpop_rev:', pop_rev

if product == "wolverine" and real_rev < 5:
	raise Exception("Too old rev!")

mct_parts = mct.parse(utils.buffer_read(bb10_boot, build_info['mct_offset'], build_info['mct_size']))

print 'Reading nvdata...'
nvram = utils.read_file_chunk(sys.argv[2], mct_parts['nvram']['offset'] - 0x200000, mct_parts['nvram']['size'])
print 'Reading cal_work...'
cal_work = utils.read_file_chunk(sys.argv[2], mct_parts['cal_work']['offset'] - 0x200000, mct_parts['cal_work']['size'])
print 'Reading cal_backup...'
cal_backup = utils.read_file_chunk(sys.argv[2], mct_parts['cal_backup']['offset'] - 0x200000, mct_parts['cal_backup']['size'])

print 'Generate HWI...'
hwi = bb.generate_hwi(product, variant, pcb_rev, pop_rev)

print 'Generate new boot partition...'

android_boot = utils.read_file('files/boot_gpt_secure.bin' if secure else 'files/boot_gpt_insecure.bin')
boot_gpt_header = gpt.decode_header(utils.buffer_read(android_boot, gpt.sector_size,  gpt._GPT_HEADER_SIZE))
boot_gpt_entires = gpt.decode_ptable(boot_gpt_header, utils.buffer_read(android_boot, gpt.lba_to_bytes(boot_gpt_header['ptable_lba']), boot_gpt_header['entries_cnt'] * boot_gpt_header['entry_size']))

boot_file_list = {
	'hwi':			(True,  hwi),
	'stage1':		(False, 'files/stage1.mbn'),
	'stage2':		(False, 'files/stage2.mbn'),
	'stage3':		(False, 'files/stage3.mbn'),
	'bbss':			(False, 'files/bbss.mbn'),
	'sbl1r':		(False, 'files/sbl1r.mbn'),
	'tzr':			(False, 'files/tz.mbn'),
	'rpmr':			(False, 'files/rpm.mbn'),
	'sdir':			(False, 'files/sdi.mbn'),
	'abootr':		(False, 'files/aboot.mbn')
}

for part in boot_gpt_entires:
	if part in boot_file_list:
		buf = b''
		if boot_file_list[part][0]:
			buf = boot_file_list[part][1]
		else:
			buf = utils.read_file(boot_file_list[part][1])

		if gpt.partition_size(boot_gpt_entires, part) < len(buf):
			raise Exception(part + ' is too big!')

		buf += utils.get_padding(buf, gpt.partition_size(boot_gpt_entires, part))

		android_boot = utils.buffer_write(android_boot, gpt.lba_to_bytes(boot_gpt_entires[part]['first_lba']), buf)

android_user = utils.read_file('files/user_gpt.bin')
user_gpt_header = gpt.decode_header(utils.buffer_read(android_user, gpt.sector_size,  gpt._GPT_HEADER_SIZE))
user_gpt_entires = gpt.decode_ptable(user_gpt_header, utils.buffer_read(android_user, gpt.lba_to_bytes(user_gpt_header['ptable_lba']), user_gpt_header['entries_cnt'] * user_gpt_header['entry_size']))

print 'Generate new user partition...'

user_file_list = {
	'nvram':		(True,  nvram),
	'calwork_b':	(True,  cal_work),
	'calback_b':	(True,  cal_backup),
	'aboot':		(False, 'files/aboot.mbn'),
	'sbl1':			(False, 'files/sbl1.mbn'),
	'rpm':			(False, 'files/rpm.mbn'),
	'tz':			(False, 'files/tz.mbn'),
	'sdi':			(False, 'files/sdi.mbn'),
	'blog':			(False, 'files/blog.img'),
	'boardid':		(False, 'files/boardid.img'),
	'nvuser':		(False, 'files/nvuser.img'),
	'perm':			(False, 'files/perm.img'),
	'prdid':		(False, 'files/prdid.img'),
	'modem':		(False, 'files/NON-HLOS.bin'),
}

for part in user_gpt_entires:
	if part in user_file_list:
		buf = b''
		if user_file_list[part][0]:
			buf = user_file_list[part][1]
		else:
			buf = utils.read_file(user_file_list[part][1])

		if gpt.partition_size(user_gpt_entires, part) < len(buf):
			raise Exception(part + ' is too big!')

		android_user = utils.buffer_write(android_user, gpt.lba_to_bytes(user_gpt_entires[part]['first_lba']), buf)

print 'Saving new boot partition...'
utils.write_file(sys.argv[3], android_boot)

print 'Saving new user partition...'
utils.write_file(sys.argv[4], android_user)

print 'Done!'
