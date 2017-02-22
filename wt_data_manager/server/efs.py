#!/usr/bin/env python

from __future__ import with_statement

import os
import sys
import errno

from fuse import FUSE, FuseOSError, Operations


class EFS(Operations):
    def __init__(self, root):
        self.root = root

    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        raise FuseOSError(errno.EPERM)

    def chown(self, path, uid, gid):
        raise FuseOSError(errno.EPERM)

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        raise FuseOSError(errno.EPERM)

    def rmdir(self, path):
        raise FuseOSError(errno.EPERM)

    def mkdir(self, path, mode):
        raise FuseOSError(errno.EPERM)

    def statfs(self, path):
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path):
        raise FuseOSError(errno.EPERM)

    def symlink(self, name, target):
        raise FuseOSError(errno.EPERM)

    def rename(self, old, new):
        raise FuseOSError(errno.EPERM)

    def link(self, target, name):
        raise FuseOSError(errno.EPERM)

    def utimens(self, path, times=None):
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        raise FuseOSError(errno.EPERM)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        raise FuseOSError(errno.EPERM)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(errno.EPERM)

    def flush(self, path, fh):
        return 0

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        return 0


def main(mountpoint, root):
    FUSE(EFS(root), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    main(sys.argv[2], sys.argv[1])