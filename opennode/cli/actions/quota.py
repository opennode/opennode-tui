#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import struct

magic_v3 = 0xfedcbc27


def read_header(fd):
    # 4+4: magic + flags
    return struct.unpack('=LL', fd[:8])


def read_1_level(fd):
    # struct dq_stat
    # Byte limits
    #  1. 8 byte - bhardlimit
    #  2. 8 byte - bsoftlimit
    #  3. 8 byte - btime (time_t)
    #  4. 8 byte - bcurrent
    # Inode limits
    #  5. 4 byte - ihardlimit
    #  6. 4 byte - isoftlimit
    #  7. 8 byte - itime (time_t)
    #  8. 4 byte - icurrent
    #  x. 4 byte - padding
    # struct dq_info
    #  9. 8 byte - bexpire (time_t)
    #  a. 8 byte - iexpire (time_t)
    #  b. 4 byte - flags
    #  x. 4 byte - padding
    return struct.unpack('=QQQQLLQLLQQLL', fd[8:88])


def read_path(fd):
    path_len = struct.unpack('=Q', fd[88:96])[0]
    return (path_len,
            struct.unpack('%ds' % path_len, fd[96:96+path_len])[0])


def read_2_level(fd):
    # TODO: 2-level quota structures (really hard, not needed for
    # checksum recalculation)
    pass


def read_ugid(fd):
    # TODO: ugid quota structures (really hard, not needed for
    # checksum recalculation)
    pass


def read_checksum(fd):
    return struct.unpack('=Q', fd[-8:])


def calc_checksum(fl):
    chksum = 0
    multiplier = 0
    # "buffer" must always be aligned to 64*1024 (65536) -
    if len(fl) < 65536:
        buf = b''.join(map(chr, fl + [0 for i in xrange(65536 - len(fl))]))
    else:
        multiplier = len(fl) / 65536
        buf = b''.join(map(chr, fl + [0 for i in xrange(len(fl) -
                                                        65536*multiplier)]))
    for x in xrange(8192*multiplier + 8192):
        chksum ^= struct.unpack('=Q', buf[x*8:x*8+8])[0]
    return struct.pack('=Q', chksum)


def copy_quota_file(ctid, new_ctid, quota_path='/var/vzquota'):
    fd = open(os.path.join(quota_path, 'quota.%s' % ctid), 'rb').read()
    if read_header(fd)[0] != magic_v3:
        print 'Only quota file format v3 is supported'
        raise
    path_len, path = read_path(fd)
    new_path = os.path.join(os.path.dirname(path), str(new_ctid))
    new_path_len = len(new_path) if len(new_path) > path_len else path_len
    fl = map(ord, fd[:88])
    fl += map(ord, struct.pack('=Q', new_path_len))
    fl += map(ord, [c for c in new_path])
    fl += map(ord, fd[(96+path_len): -8])
    chksum = calc_checksum(fl + [0 for i in range(8)])
    fl += map(ord, [i for i in chksum])
    with open(os.path.join(quota_path, 'quota.%s' % new_ctid), 'wb') as f:
        f.write(b''.join(map(chr, fl)))


def rename_quota_file(ctid, new_ctid, quota_path='/var/vzquota'):
    copy_quota_file(ctid, new_ctid)
    os.unlink(os.path.join(quota_path, 'quota.%s' % ctid))
