#!/usr/bin/env python

from __future__ import with_statement
import struct
import sys
import os

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

file_num = 0
while file_num < file_count:
    folder_path, filename, file_hash, file_offset, file_size = files2[file_num]
    if filename.endswith('.png'):
        print "%s\\%s hash=%08X offset=%d length=%d" % \
            (folder_path, filename, file_hash, file_offset, file_size)
        with open(filename, 'w') as f2:
            f.seek(1 + file_offset + len(folder_path) + len(filename) + 12)
            f2.write(f.read(file_size))
    file_num += 1

