import os

def read_file(filename):
	if len(filename) > 6 and filename[:6] == 'files/':
		try:
			base_path = sys._MEIPASS
		except Exception:
			base_path = os.path.dirname(os.path.abspath(__file__))
		filename = base_path + '/' + filename
	filename = filename.replace('/', os.sep)
	f = open(filename, "rb")
	data = f.read()
	f.close()
	return data

def read_file_chunk(filename, start, size):
	f = open(filename, "rb")
	f.seek(start)
	if f.tell() != start:
		raise Exception("file too small")
	data = f.read(size)
	f.close()
	return data

def write_file(filename, data):
	f = open(filename, "wb")
	f.write(data)
	f.close()

def buffer_read(buf, offset, size):
	if len(buf) < offset + size:
		raise Exception("buffer too small")
	return buf[offset : offset + size]

def get_padding(buf, new_size):
	if len(buf) > new_size:
		return b''
	return (new_size - len(buf)) * '\0'

def buffer_write(buf, offset, value):
	buf += get_padding(buf, offset)
	return buf[:offset] + value + buf[offset + len(value):]
    
def hex(num):
    return "0x{num:x}".format(num = num)