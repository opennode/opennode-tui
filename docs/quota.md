Quota files
===========

Quota files are used to track quota status and info about given OpenVZ container.
When copying/moving containers to new ctid there are few ways to handle quota.

| Action | Result |
|--------|--------|
| Keep old quota.<ctid>  | When new container is started, quotas are re-calulated and it may take long time. |
| Rename quota.<ctid>    | Container may not start due incorrect path inside quota.<ctid> |
| Rename quota.<ctid> and fix path inside  quota file | Container may not start due corrupt checksum. |
| Rename quota.<ctid>, fix path and recalculate checksum | Container should start normally, without recalulating quotas. |


Structure
=========

Quota files are in binary format. Currently we only handle version 3.

| Field | Size (bytes) | Offset | Comment |
|---|---|---|---|
| magic | 0 | 4 | Magic number, 0xFEDCBC27 for v3 |
| flags | 4 | 4 | |
| bhardlimit | 8 | 8 | Absolute limit in bytes |
| bsoftlimit | 8 | 16 | Preferred limit in bytes |
| btime | 8 | 24 | Time limit for excessive disk use |
| bcurrent | 8 | 32 | Current bytes count |
| ihardlimit | 4 | 40 | Absolute limit on allocated inodes |
| isoftlimit | 4 | 44 | Preferred inode limit |
| itime | 8 | 48 | Time limit for excessive inode use |
| icurrent | 4 | 56 | Current # of allocated inodes |
| padding | 4 | 60 | |
| bexpire | 8 | 64 | Expire timeout for excessive disk use |
| iexpire | 8 | 72 | Expire timeout for excessive inode use |
| flags | 4 | 80 | Warnings printed (0x01 - inode, 0x02 space) |
| padding | 4 | 84 | |
| path length | 8 | 88 | Length for private path string |
| path | n | 96 | Privat area path |
| ugid info | ? | 96+n | 2-level quota info |
| ugid stat | ? | ? | ugid objects |
| checksum | 8 | EOF-8 | Checksum of quota file |

Checksum
========

Checksum is simple:

    chksum = 0
    while !eof:
        chksum = chksum xor (read next 8 bytes form file buffer)

Buffer is aligned to 64k boundary so it always contains 8 divisable number of bytes.