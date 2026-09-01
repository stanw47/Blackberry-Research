import struct, sys, utils
from collections import OrderedDict

_BUILD_INFO_FORMAT = "<II4sI64s16s16s12sIIIIIIIIIIIIIIIIIIIIII40s1024s"
_REV_TABLE_FORMAT = "<BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

def _update_checksum(chksum, data):
	for c in data:
		chksum = ((0x1000193 * chksum) ^ ord(c)) & 0xFFFFFFFF
	return chksum

def generate_hwi(product, variant, pcb_rev, pop_rev):
	hwi_entries = OrderedDict()
	hwi_entries['product'] = product
	hwi_entries['variant'] = variant
	hwi_entries['pcb_rev'] = str(pcb_rev)
	hwi_entries['pop_rev'] = str(pop_rev)
	hwi_entries['bsis_type'] = 'bsis_lite'

	# FNV1a hash
	chksum = 0x811C9DC5
	hwi = ''
	for key in hwi_entries:
		hwi += key + ' = ' + hwi_entries[key] + '\n'
		chksum = _update_checksum(chksum, key)
		chksum = _update_checksum(chksum, hwi_entries[key])

	hwi += '\n# The checksum gets added at the end of the file by hwi_validate\n'
	hwi += 'chksum = ' + utils.hex(chksum) + '\n'

	return hwi

def parse_build_info(build_info):
	build_info = struct.unpack(_BUILD_INFO_FORMAT, build_info)
	if build_info[1] != 0x4fc: # size
		raise Exception("Invalid build info size")

	return {
		'version'         : str(ord(build_info[2][0])) + '.' + str(ord(build_info[2][1])) + '.' + str(ord(build_info[2][2])) + '.' + str(ord(build_info[2][3])),
		'hwid'            : build_info[3],
		'builder'         : str(build_info[5].decode('UTF-8').split('\0', 1)[0]),
		'date'            : str(build_info[6].decode('UTF-8').split('\0', 1)[0]) + ' ' + str(build_info[7].decode('UTF-8').split('\0', 1)[0]),
		'secure'          : build_info[8] == 0,
		'rev_table_offset': build_info[18] - build_info[15] * 4 - build_info[13] * 2,
		'rev_table_size'  : build_info[13] * 2,
		'mct_offset'      : build_info[18] - build_info[15] * 4,
		'mct_size'        : build_info[15] * 4,
		'processor_id'    : build_info[20],
		'usbloader_id'    : build_info[24],
	}

def parse_rev_table(rev_table):
	rev_table = struct.unpack(_REV_TABLE_FORMAT, rev_table)
	ret = {}
	for i in range(20):
		key, value = rev_table[i * 2], rev_table[i * 2 + 1]
		if key == 0xff:
			continue
		if key == 1:
			key = 'pcb_rev'
		if key == 4:
			key = 'pop_rev'
		ret[key] = value
	return ret

def hwid_to_product(hwid):
	if hwid == 0x84002c0a or hwid == 0x85002c0a or hwid == 0x86002c0a or hwid == 0x87002c0a or hwid == 0x8c002c0a:
		return "wolverine" # called windermere in BB10
	if hwid == 0x8d002c0a or hwid == 0x8e002c0a or hwid == 0x8f002c0a:
		return "oslo" # called windermere2, windermere3 and windermere4 in BB10
	if hwid == 0xb400240a or hwid == 0xb600240a or hwid == 0xb700240a or hwid == 0xbc00240a or hwid == 0xae00240a or hwid == 0xaf00240a:
		return "mockingbird" # called ontario in BB10
	if hwid == 0xa400080a:
		return "devalphax"
	# keian ?
	raise Exception("unknown hwid: " + utils.hex(hwid))

def hwid_to_variant(hwid):
	if hwid == 0x84002c0a or hwid == 0xae00240a: # SQW100-3
		return "na"
	if hwid == 0x85002c0a or hwid == 0xaf00240a: # SQW100-2
		return "vzw"
	if hwid == 0x86002c0a or hwid == 0xb400240a:
		return "sprint"
	if hwid == 0x87002c0a: # SQW100-1
		return "emea"
	if hwid == 0x8c002c0a:
		return "wichita"
	if hwid == 0x8d002c0a or hwid == 0x8e002c0a or hwid == 0x8f002c0a: # SQW100-4
		return "row"
	if hwid == 0xa400080a:
		return ""
	if hwid == 0xb600240a:
		return "fdd"
	if hwid == 0xbc00240a:
		return "tdd"
	raise Exception("unknown hwid: " + utils.hex(hwid))

wolverine_na_table = {
	6: 3,
	7: 4,
	8: 4,
	9: 5,
}

wolverine_vzw_table = {
	2: 1,
	7: 1,
	3: 2,
	4: 3,
	5: 3,
	6: 3,
	8: 4,
	9: 4,
	10: 4,
}

wolverine_emea_table = {
	3: 2,
	4: 3,
	5: 3,
	6: 3,
	7: 4,
	8: 4,
}

def wolverine_pcb_rev_to_real_rev(variant, rev):
	table = None
	if variant == "na":
		table = wolverine_na_table
	if variant == "vzw":
		table = wolverine_vzw_table
	if variant == "emea":
		table = wolverine_emea_table
	if table == None:
		return rev
	if rev in table:
		return table[rev]
	return rev
