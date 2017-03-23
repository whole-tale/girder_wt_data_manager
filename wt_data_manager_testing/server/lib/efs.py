#!/usr/bin/env python

from __future__ import with_statement

import os
import stat
import sys
import errno
import threading
import ctypes
try:
    import httplib
except ImportError:
    import http.client as httplib
import time
from dateutil.parser import parse
import json
import traceback

from fuse import FUSE, FuseOSError, Operations

C_FUSE_SUPER_MAGIC = 0x65735546
ST_RDONLY = 1
ST_NOSUID = 2
ST_NODEV = 4
ST_NOEXEC = 8
ST_NOATIME = 1024
ST_NODIRATIME = 2048

ST_OPTS = ST_RDONLY + ST_NOSUID + ST_NODEV + ST_NOEXEC + ST_NOATIME + ST_NODIRATIME

class EFS(Operations):
    DM_GET_SESSION_URL = ""
    def __init__(self, sessionId, root, restUrl, token):
        self.sessionId = sessionId
        self.root = root
        self.restUrl = restUrl
        (self.secure, self.serverUrl) = self.getServerUrl(restUrl)
        self.token = token
        self.logFile = open("fuse-" + self.sessionId + ".log", "w")
        self.log("restUrl: " + restUrl)
        self.headers = {
            "Accept": "application/json",
            "Girder-Token": self.toAscii(token)
        }
        self.sessionInfo = self.getSessionInfo()
        self.uid = os.getuid()
        self.gid = os.getgid()
        self.ctime = int(time.time())
        self.locks = {}

    def toAscii(self, str):
        if isinstance(str, unicode):
            return str.encode("ascii", "replace")
        else:
            return str

    def getSessionInfo(self):
        return json.loads(self.get("dm/session/" + self.sessionId))

    def get(self, path):
        return self.request("GET", path)
    
    def post(self, path):
        return self.request("POST", path)
    
    def delete(self, path):
        return self.request("DELETE", path)
        
        
    def request(self, method, path):
        if self.secure:
            conn = httplib.HTTPSConnection(self.serverUrl)
        else:
            conn = httplib.HTTPConnection(self.serverUrl)
        requestUrl = "/api/v1/" + path
        self.log("Getting " + self.serverUrl + requestUrl + ". Headers: " + str(self.headers))
        conn.request(method, requestUrl, "", self.headers)
        resp = conn.getresponse()
        self.log("Response status: " + str(resp.status))
        body = resp.read()
        if resp.status != 200:
            raise Exception("Request error " + str(resp.status) + ": " + body)
        self.log("Response body: " + str(body))
        conn.close()
        return body


    def getServerUrl(self, restUrl):
        return (False, "localhost:8080")
        ix = restUrl.find("/api/v1")
        if ix > 0:
            if restUrl.find('http://') != -1:
                return (False, restUrl[7:ix])
            elif restUrl.find('https://') != -1:
                return (True, restUrl[8:ix])
        raise Exception("Cannot find server url in '" + str(restUrl) +
            "'. Expected something of the form http[s]://<host>[:<port>]/api/v1")


    def getObject(self, path, children = False):
        if path == "/":
            return {
                "object": {
                    "updated": self.ctime,
                    "created": self.ctime,
                    "size": len(self.sessionInfo["dataSet"]),
                    "type": "folder"
                }
            }
        else:
            return self.getObjectRest(path, children)
    
    def getObjectRest(self, path, children):
        if children:
            return json.loads(self.get("dm/session/" + self.sessionId + "/object?children=true&path=" + path))
        else:
            return json.loads(self.get("dm/session/" + self.sessionId + "/object?path=" + path))
    
    def lockObject(self, path):
        obj = self.getObjectRest(path, False)
        resp = self.acquireLock(obj["object"]["_id"])
        self.log("lockObject response: " + str(resp))
        return resp["_id"]
    
    def acquireLock(self, itemId):
        return json.loads(self.post("dm/lock?sessionId=" + self.sessionId + "&itemId=" + itemId))
    
    def unlockObject(self, lockId):
        return json.loads(self.delete("dm/lock/" + lockId))
        
    def waitForFile(self, path):
        while True:
            result = self.getObjectRest(path, False)
            if not "object" in result:
                raise Exception("Invalid response: " + str(result))
            obj = result["object"]
            if "dm" in obj and "cached" in obj["dm"]:
                return obj["dm"]["psPath"]
            else:
                time.sleep(1.0)

    def log(self, msg):
        self.logFile.write(msg)
        self.logFile.write("\n")
        self.logFile.flush()
        print(str(msg) + "\n")

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        self.log("access(" + str(path) + ", " + str(mode) + ")")
        if mode & os.W_OK:
            self.log("EACCESS")
            raise FuseOSError(errno.EACCES)
        if mode & os.X_OK:
           return 0
        if path == "/":
            return 0
        self.log("EACCESS")
        raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        raise FuseOSError(errno.EPERM)

    def chown(self, path, uid, gid):
        raise FuseOSError(errno.EPERM)

    def getattr(self, path, fh=None):
        self.log("getattr(" + str(path) + ", " + str(fh) + ")")

        obj = self.getObject(path, False)
        print("getattr: obj: " + json.dumps(obj))
        obj = obj["object"]
        
        d = {
            "st_atime": self.getTime(obj["updated"]),
            "st_mtime": self.getTime(obj["updated"]),
            "st_ctime": self.getTime(obj["created"]),
            "st_mode": self.getMode(obj),
            "st_nlink": 1,
            "st_size": obj["size"],
            "st_uid": self.uid,
            "st_gid": self.gid,
        }
        print(d)
        print(os.statvfs("/tmp/file"))
        return d
    
    def getTime(self, obj):
        if isinstance(obj, (int, long)):
            return obj
        else:
           #return int(datetime.strptime(obj, "%Y-%m-%dT%H:%M:%S.f%z").strftime("%s"))
           return int(parse(obj).strftime("%s"))
    
    
    def getMode(self, obj):
        if obj["type"] == "file":
            return 0o444 + stat.S_IFREG
        else:
            return 0o555 + stat.S_IFDIR

    def readdir(self, path, fh):
        self.log("readdir(" + str(path) + ", " + str(fh) + ")")
        if path == "/":
            for r in self.readRootDir():
                yield r
            return

        dirents = [".", ".."]
        obj = self.getObject(path, True)
        for c in obj["children"]:
            dirents.append(str(c["name"]))
        print("dirents: " + str(dirents))
        for r in dirents:
            yield r

    def readRootDir(self):
        l = ["."]
        for obj in self.sessionInfo["dataSet"]:
            l.append(self.stripSlash(obj["mountPath"]))
        for obj in l:
            print(obj)
            yield obj
    
    def stripSlash(self, str):
        if str[0] == "/":
            return str[1:]
        else:
            return str


    def readlink(self, path):
        self.log("readlink(" + str(path) + ")")
        # we shouldn't be here
        raise FuseOSError(errno.EACCESS)

    def mknod(self, path, mode, dev):
        raise FuseOSError(errno.EPERM)

    def rmdir(self, path):
        raise FuseOSError(errno.EPERM)

    def mkdir(self, path, mode):
        raise FuseOSError(errno.EPERM)

    def statfs(self, path):
        self.log("statfs(" + str(path) + ")")
        return {
           "f_type": C_FUSE_SUPER_MAGIC,
           "f_bsize": 4096,
           #"f_blocks": 200000000,
           "f_bfree": 0,
           "f_bavail": 0,
           "f_files": 1000000,
           "f_ffree": 0,
           "f_fsid": 0,
           "f_namemax": 255,
           "f_flags": ST_OPTS
        }

    def unlink(self, path):
        raise FuseOSError(errno.EPERM)

    def symlink(self, name, target):
        raise FuseOSError(errno.EPERM)

    def rename(self, old, new):
        raise FuseOSError(errno.EPERM)

    def link(self, target, name):
        raise FuseOSError(errno.EPERM)

    def utimens(self, path, times=None):
        raise FuseOSError(errno.EPERM)

    # File methods
    # ============

    def open(self, path, flags):
        self.log("open(" + str(path) + ", " + str(flags) + ")")
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_EXCL | os.O_TRUNC):
            raise FuseOSError(errno.EPERM)
        lockId = self.lockObject(path)
        try:
            pfsPath = self.waitForFile(path)
            print("Opening file " + pfsPath)
            handle = os.open(pfsPath, flags)
            self.locks[handle] = lockId
            return handle
        except Exception as ex:
            traceback.print_exc()
            self.unlockObject(lockId)

    def create(self, path, mode, fi=None):
        raise FuseOSError(errno.EPERM)

    def read(self, path, length, offset, fh):
        self.log("read(" + str(path) + ", " + str(length) + ", " + str(offset) + ", " + str(fh) + ")")
        os.lseek(fh, offset, os.SEEK_SET)
        data = os.read(fh, length)
        print("Read: " + data)
        return data

    def write(self, path, buf, offset, fh):
        raise FuseOSError(errno.EPERM)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(errno.EPERM)

    def flush(self, path, fh):
        return 0

    def release(self, path, fh):
        self.log("release(" + str(path) + ", " + str(fh) + ")")
        result = os.close(fh)
        if fh in self.locks:
            lockId = self.locks[fh]
            self.unlockObject(lockId)
        else:
            raise Exception("Could not find lockId for file handle " + str(fh))
        return result

    def fsync(self, path, fdatasync, fh):
        return 0


class EFSThread(threading.Thread):
    def __init__(self, sessionId, mountpoint, psRoot, restUrl, token):
        threading.Thread.__init__(self)
        self.daemon = True
        self.sessionId = sessionId
        self.mountpoint = mountpoint
        self.psRoot = psRoot
        self.restUrl = restUrl
        self.token = token

    def run(self):
        FUSE(EFS(self.sessionId, self.psRoot, self.restUrl, self.token),
             self.mountpoint, nothreads=True, foreground=True)

    def stop(self):
        if not self.isAlive():
            return

        exc = ctypes.py_object(KeyboardInterrupt)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(self.ident), exc)
        if res == 0:
            raise ValueError("Somebody is lying about a thread id")
        elif res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

__EFS_INSTANCES__ = {}
__EFS_LOCK__ = threading.Lock()
__EFS_ID_COUNTER__ = 0

def mount(sessionId, mountpoint, psRoot, restUrl, token):
    global __EFS_ID_COUNTER__, __EFS_LOCK__, __EFS_INSTANCES__
    try:
        os.mkdir(mountpoint)
    except OSError:
        pass
    instanceId = None
    thread = None
    with __EFS_LOCK__:
        thread = EFSThread(sessionId, mountpoint, psRoot, restUrl, token)
        __EFS_INSTANCES__[__EFS_ID_COUNTER__] = thread
        instanceId = __EFS_ID_COUNTER__
        __EFS_ID_COUNTER__ = __EFS_ID_COUNTER__ + 1
    thread.start()
    return instanceId

def unmount(instanceId):
    global __EFS_ID_COUNTER__, __EFS_LOCK__, __EFS_INSTANCES__
    thread = None
    with __EFS_LOCK__:
        if instanceId in __EFS_INSTANCES__:
            thread = __EFS_INSTANCES__[instanceId]
            del __EFS_INSTANCES__[instanceId]
    if thread != None:
        thread.stop()
        try:
            os.rmdir(thread.mountpoint)
        except OSError:
            pass

if __name__ == "__main__":
    sessionId = sys.argv[1]
    token = sys.argv[2]
    print("SessionId: " + sessionId)
    print("Token: " + token)
    FUSE(EFS(sessionId, "/tmp", "http://localhost:8080/api/v1", token), "fuse/test", nothreads=True, foreground=True)
