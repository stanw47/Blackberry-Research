import sys, struct

def parse(mct):
	partitions = {}
	magic = struct.unpack('<I', mct[:4])[0]
	if magic != 0x92be564a:
		raise Exception('Invalid MCT magic')

	minor, major = struct.unpack('<HH', mct[4:8])
	if major != 1:
		raise Exception('Invalid MCT major version')

	mct = mct[8:]
	while len(mct) > 0:
		_type, size = struct.unpack('<BB', mct[:2])
		if _type == 9 or _type == 0xff:
			break

		if size > len(mct):
			raise Exception('Invalid MCT entry')

		if _type == 0x39:
			unk, flags, name, start, end = struct.unpack('<BB12sII', mct[2:size])
			name = str(name.decode('UTF-8').split('\0', 1)[0])

			if not name in partitions:
				partitions[name] = { 'offset': start << 16, 'size': ((end + 1) << 16) - (start << 16) }
		mct = mct[size:]

	return partitions