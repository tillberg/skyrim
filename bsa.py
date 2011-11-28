#!/usr/bin/env python

from __future__ import with_statement
import struct
import sys
import os
import zlib

if len(sys.argv) == 2:
    BSA_FILE = sys.argv[1]
else:
    print "usage: %s <bsa-file>" % sys.argv[0]
    sys.exit(1)

HEADER_LENGTH = 0x24

f = open(BSA_FILE)
header = f.read(HEADER_LENGTH)

bsa, version, offset, flags1, folder_count, file_count, folder_names_length, \
    file_names_length, flags2 = struct.unpack("<4sLLLLLLLL", header)

assert bsa == "BSA\x00"
assert version == 104
assert offset == HEADER_LENGTH

folders = [struct.unpack("<QLL", f.read(16)) for i in range(folder_count)]

files = []

for folder_hash, folder_file_count, folder_offset in folders:
    folder_path_length = ord(f.read(1))
    folder_path = f.read(folder_path_length)[:-1]
    
    for i in range(folder_file_count):
        file_hash, file_size, file_offset = struct.unpack("<QLL", f.read(16))
        files.append((file_hash, file_size, file_offset, folder_path))

assert folder_count == len(folders)
assert file_count == len(files)

file_num = 0 
current_filename = ""
files2 = []
while file_num < file_count:
    ch = f.read(1)
    if ch == "\x00":
        file_hash, file_size, file_offset, folder_path = files[file_num]
        files2.append((folder_path, current_filename, file_hash, file_offset, file_size))
        current_filename = ""
        file_num += 1
    else:
        current_filename += ch

def parsePngHeaders(data):
    if len(data):
        length = struct.unpack(">L", data[0:4])[0]
        chunktype = data[4:8]
        chunk = data[8:(8 + length)]
        #crc = struct.unpack(">L", data[(8 + length):(8 + length + 4)])
        print '%s: %s bytes' % (chunktype, length)
        offset = 12 + length
        if chunktype == 'IDAT':
            # We're looking now at the data chunk, which is followed immediately
            # by the IEND chunk.  The length of the data chunk should correspond
            # to the actual distance to the IEND code in the data stream.  Using
            # this, we can calculate how many extra bytes are inserted in the file.
            real_offset = data.find('IEND') - 4
            print 'offset: %s, real: %s' % (offset, real_offset)
            #offset = real_offset
            return (real_offset - offset, chunk)
        else:
            return parsePngHeaders(data[(offset):])
    else:
        return (None, None)

#with open('test.png') as tf:
#    data = tf.read()
#    chunk = parsePngHeaders(data[8:])
#    zlib.decompress(chunk)

file_num = 0
html = open('pics.html', 'w')
html.write('<style>img { float: left; border: 1px solid black; height: 200px; width: 200px; }</style>')
while file_num < file_count:
    folder_path, filename, file_hash, file_offset, file_size = files2[file_num]
    if filename.endswith('letter.png'):
        print "%s\\%s hash=%08X offset=%08X length=%08X" % \
            (folder_path, filename, file_hash, file_offset, file_size)
        html.write('<img src="%s">' % filename)
        with open(filename, 'w') as pngfile:
            # The offset given by the BSA headers above are all 1 byte off of actual file offsets
            # Beyond that, there is a header for each file that includes the folder path, filename,
            # and 12 assorted extra bytes of who knows what.
            f.seek(file_offset)
            data = f.read(file_size)
            header_size = 1 + len(folder_path) + len(filename) + 12
            d = data[header_size:]
            # Here, we're going to selectively cut out five byte segments of the data stream.  I have
            # no idea what these 5 byte chunks are, but at least for m_letter.png, these offsets work.
            # It's... close to 0x4030 jumps, but not consistent.  For some other files, especially 
            # the larger PNGs, something else is going on, as the differences between the PNG headers
            # are misaligned by non-multiples of 5.
            index = 0x403b
            index2 = 0x8070
            index3 = 0xc0a0
            index4 = 0x100d0
            pngdata = d[0:(index-5)] + d[(index):(index2 - 5)] + d[(index2):(index3 - 5)] + d[(index3):(index4 - 5)] + d[(index4):0x14000]
            #pngfile = d[5:0x4000] + d[0x4005:0x8000] + d[0x8005:0xc000] + d[0xc005:0x10000] + d[0x10005:0x14000]
            pngfile.write(pngdata)
            diff, chunk = parsePngHeaders(pngdata[8:])
            delta = (len(pngdata) >> 14) * 5 - diff if diff is not None else None
            print 'diff: %s, delta from exp: %s' % (diff, delta)
            # parsePngHeaders returns the amount that the size of the last chunk was off by as well
            # as the data chunk from the png.  This should be zlib decrompressible.
            try:
                zlib.decompress(chunk)
                print 'success!'
            except:
                pass
    file_num += 1

