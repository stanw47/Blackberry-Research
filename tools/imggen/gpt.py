import struct, binascii, uuid
from collections import OrderedDict

_GPT_HEADER_FORMAT = "<8sIIIIQQQQ16sQIII"
_GPT_HEADER_SIZE = struct.calcsize(_GPT_HEADER_FORMAT)
_GPT_ENTRY_FORMAT = "<16s16sQQQ72s"
_GPT_ENTRY_SIZE = struct.calcsize(_GPT_ENTRY_FORMAT)
_SUPPORTED_GPT_REVISION = 0x10000

sector_size = 512

def _stringify_uuid(binary_uuid):
    return str(uuid.UUID(bytes_le = binary_uuid)).upper()

def _calc_header_crc(raw_hdr):
    raw_hdr = list(raw_hdr)
    raw_hdr[3] = 0
    raw_hdr = struct.pack(_GPT_HEADER_FORMAT, *raw_hdr)

    return binascii.crc32(raw_hdr) & 0xFFFFFFFF

def decode_header(raw_hdr):
    raw_hdr = struct.unpack(_GPT_HEADER_FORMAT, raw_hdr)

    if raw_hdr[0] != 'EFI PART':
        raise Exception("GPT partition table not found")

    if raw_hdr[1] != _SUPPORTED_GPT_REVISION:
        raise Exception("Unsupported GPT revision '%x', supported revision " \
                         "is '%s'" % \
                          (raw_hdr[1],
                           _SUPPORTED_GPT_REVISION))

    if raw_hdr[2] != _GPT_HEADER_SIZE:
        raise Exception("Bad GPT header size: %d bytes, expected %d" % \
                         (raw_hdr[2], _GPT_HEADER_SIZE))

    crc = _calc_header_crc(raw_hdr)
    if raw_hdr[3] != crc:
        raise Exception("GPT header crc mismatch: %#x, should be %#x" % \
                         (crc, raw_hdr[3]))

    return { 'signature'   : raw_hdr[0],
             'revision'    : raw_hdr[1],
             'hdr_size'    : raw_hdr[2],
             'hdr_crc'     : raw_hdr[3],
             'hdr_lba'     : raw_hdr[5],
             'backup_lba'  : raw_hdr[6],
             'first_lba'   : raw_hdr[7],
             'last_lba'    : raw_hdr[8],
             'disk_uuid'   :_stringify_uuid(raw_hdr[9]),
             'ptable_lba'  : raw_hdr[10],
             'entries_cnt' : raw_hdr[11],
             'entry_size'  : raw_hdr[12],
             'ptable_crc'  : raw_hdr[13] }

def decode_ptable(header, raw_ptable):
	crc = binascii.crc32(raw_ptable) & 0xFFFFFFFF
	if header['ptable_crc'] != crc:
		raise Exception("GPT ptable crc mismatch: %#x, should be %#x" % (crc, header['ptable_crc']))

	gpt_entires = OrderedDict()

	for index in xrange(0, header['entries_cnt']):
		start = header['entry_size'] * index
		end = start + header['entry_size']
		raw_entry = struct.unpack(_GPT_ENTRY_FORMAT, raw_ptable[start:end])
		part_name = str(raw_entry[5].decode('UTF-16').split('\0', 1)[0])

		if part_name == "":
			continue

		entry = { 'index'       : index,
				  'offs'        : header['ptable_lba'] * sector_size + start,
				  'type_uuid'   : _stringify_uuid(raw_entry[0]),
				  'part_uuid'   : _stringify_uuid(raw_entry[1]),
				  'first_lba'   : raw_entry[2],
				  'last_lba'    : raw_entry[3],
				  'flags'       : raw_entry[4] }
		gpt_entires[part_name] = entry
	return gpt_entires

def lba_to_bytes(lba):
     return lba * sector_size

def partition_size(ptable, name):
     return lba_to_bytes((ptable[name]['last_lba'] - ptable[name]['first_lba'] + 1))