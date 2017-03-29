## Data Management Plugin for Girder/WholeTale

### Intro

For details about terminology (e.g., PS, DM, etc.), see https://docs.google.com/document/d/1AWK80HqiSUdK_fKF30ysilHWl5krzPTVmK8g_3pdFeI/edit#heading=h.e5nw0hx7dnhc

There are two plugins: wt_data_manager and wt_data_manager_testing. The testing
plugin is a very dirty interface to the DM. It's not meant to be supported,
unless we decide otherwise.

The basic flow would be something like this:

* Create a session
* Start a container/notebook/tale and pass it the session id
* Mount the EFS using information from the session dataSet
* Use session/{id}/object calls to navigate the filesystem and get directory
and file information
* On open() create a lock on the Girder item using the ``lock`` API
* Wait until item.dm.cached is true, then use item.dm.psPath to get the
file bytes through some means
* Optionally monitor transfers using the ``transfer`` API
* On close, remove the lock from the item (unless the tale is saved, in which
case a new lock should be added, possibly in another session)
* When the tale is removed, delete the session

### Configuration

wt_data_manager has the following configuration options, exposed through the standard Girder plugin configuration interface:

#### dm.private_storage_path

Points to a local path where the PS is located.

#### dm.private_storage_capacity

The amount, in bytes, of storage allocated for the PS. This is used in
various cache calculations

#### dm.gc_run_interval

For file garbage collectors that run periodically (descendants of
``lib.file_gc.PeriodicFileGC``), this represents the approximate amount
of time between GC invocations.

#### dm.gc_collect_start_fraction

For certain file GC strategies, this indicates the percentage of
``dm.private_storage_capacity`` when the GC should kick-in. If the usage of
the PS is below this threshold, no GC-ing would occur.

#### dm.gc_collect_end_fraction

Once the GC process starts, it will continue until either there are no more
items that can be collected, or the PS usage drops below the percentage
indicated by this setting


### Non-REST API

Some calls to the DM API, in particular calls that are likely to be made
from other Girder/WT APIs, can be accessed through ``info['apiRoot'].dm``.
The following methods are currently implemented:

```python
DM.createSession(user, dataSet)
```

where ``dataSet`` is a list of dictionaries with keys ``itemId`` and
``mountPoint``, where ``itemId`` is a Girder item or folder id and
``mountPoint`` is an absolute path where the item/folder are mounted in the
EFS.

```python
DM.deleteSession(user, session = None, sessionId = None)
```

Deletes a session. One of ``session`` or ``sessionId`` must be non-null.

Example:

```python
dm = info['apiRoot'].dm

dataSet = [
    {'itemId': '58b08d98cbb11e6d0f95df9f', 'mountPoint': '/x/y/z'},
    {'itemId': '582f621ccbb11e75430a89ae', 'mountPoint': '/myfile.dat'}
]

session = dm.createSession(user, dataSet)
...
dm.deleteSession(user, session = session)
```

### Sessions

A session encapsulates the set of files that can be accessed by a tale. There
should be a one-to-one correspondence between a tale instance an a session.
Before a tale instance is created, a session must be created. Then, a tale
instance can use the session identifier to inform the DM about various needs
related to files as well as get the status of files when necessary.

All REST endpoints have corresponding methods in the respective Girder model.

The session API is:

#### Create session
```
POST /dm/session
```

Parameters:
```json
dataSet=[{"itemId": <itemOrFolderId>, "mountPath": <absolutePath>}, ...]
```

Example:
```
curl -X POST -G --header 'Content-Length: 0' --header 'Accept: application/json' \
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr' \
    --data-urlencode \
    'dataSet=[\
      {"itemId": "58acccc7cbb11e4425ce147b", "mountPath": "/one"},\
      {"itemId": "58acccc7cbb11e4425ce148b", "mountPath": "/fa.txt"}]'\
    'http://localhost:8080/api/v1/dm/session'
```
Example Response:
```json
{
    "_id": "58d2e27dcbb11e37037227bd",
    "access": {
        "groups": [],
        "users": [
            {"id": "582f621ccbb11e75430a89ae", "level": 2}
        ]
    },
    "dataSet": [
        {"itemId": "58acccc7cbb11e4425ce147b", "mountPath": "/one"},
        {"itemId": "58acccc7cbb11e4425ce148b", "mountPath": "/fa.txt"}
    ],
    "ownerId": "582f621ccbb11e75430a89ae"
}
```

#### List sessions

```
GET /dm/session
```

Example:

```
curl -X GET --header 'Accept: application/json' \
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/session
```

Example response:
```json
[
    {
        "_accessLevel": 2,
        "_id": "58c06618cbb11e3152f13d23",
        "_modelType": "session",
        "dataSet": [
            {"itemId": "58b08d98cbb11e6d0f95df90", "mountPath": "/one"},
            {"itemId": "58b08d98cbb11e6d0f95dfa0", "mountPath": "/fa.txt"}
        ],
        "ownerId": "582f621ccbb11e75430a89ae"
    },
    ...
]
```

#### Get session

```
GET /dm/session/{id}
```

Example:
```
curl -X GET --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/session/58d2e630cbb11e3ba1e91b26'
```

Example response:

```json
{
    "_accessLevel": 2,
    "_id": "58d2e630cbb11e3ba1e91b26",
    "_modelType": "session",
    "dataSet": [
        {"itemId": "58acccc7cbb11e4425ce147b", "mountPath": "/one"},
        {"itemId": "58acccc7cbb11e4425ce148b", "mountPath": "/fa.txt"}
    ],
    "ownerId": "582f621ccbb11e75430a89ae"
}
```

#### Remove session

```
DELETE /dm/session/{id}
```

Example:

```
curl -X DELETE --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/session/58d2e630cbb11e3ba1e91b26'
```

There is no response on success.

#### Get object

Returns either a Girder item or a Girder folder that can be found at a
specified path. The path is absolute and is composed of a mount point in
the session data set followed, optionally, by names of Girder folders, and
ending, optionally, in a Girder item name, separated by forward slashes. If
the children parameter is present, then the result also contains a listing
of all the children of the specified path.

```
GET /dm/session/{id}/object
```

Parameters:
```
path=/<mountPath>[/<folderName>]*[/<itemName>]?
children=
```

Example:

```
curl -X GET --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/session/58d2d65dcbb11e24580bf6f2/object?path=/one&children'
```

Example response:

```json
{
    "object": {
        "_id": "58b08d98cbb11e6d0f95df90",
        "access": {...},
        "baseParentId": "58437831cbb11e77de91cccb",
        "baseParentType": "collection",
        "created": "2017-02-24T19:46:32.884000+00:00",
        "creatorId": "582f621ccbb11e75430a89ae",
        "description": "",
        "lowerName": "a",
        "name": "a",
        "parentCollection": "collection",
        "parentId": "58437831cbb11e77de91cccb",
        "public": true,
        "size": 12,
        "type": "folder",
        "updated": "2017-02-24T19:46:32.884000+00:00"
    },
    "children": [
        {
            "_id": "58b08d98cbb11e6d0f95df91",
            "access": {...},
            "baseParentId": "58437831cbb11e77de91cccb",
            "baseParentType": "collection",
            "created": "2017-02-24T19:46:32.886000+00:00",
            "creatorId": "582f621ccbb11e75430a89ae",
            "description": "",
            "lowerName": "c",
            "name": "c",
            "parentCollection": "folder",
            "parentId": "58b08d98cbb11e6d0f95df90",
            "public": true,
            "size": 23,
            "updated": "2017-02-24T19:46:32.886000+00:00"
        },
        ...
    ],
}
```

### Locks

Locks control how the cache works. Basically, if a file has at least one lock,
then it cannot be deleted from the cache. The authoritative lock count is
kept in the Girder item and is called ``dm.lockCount``. A separate collection,
``lock`` is kept with details about lock ownership. The usefulness of the
lock collection should mostly be in the ability to keep track of who holds
locks on what. There is currently no reconciliation mechanism between the two,
but the model updates both in sync (to the extent that the server isn't brought
down between calls).

In particular, at least when debugging, it is quite likely to get in a
situation when locks are not released because the container/FUSE layer is
terminated when a file is open, but before it gets a chance to close it. This
requires some form of garbage collection on the locks, by tracking the
existence of lock owners/sessions. This isn't there. It probably requires some
discussion.

The API is:

#### Acquire lock

This is typically called in response to an ``open()`` request in the filesystem.
The current implementation waits for any pending deletes on the file, then
triggers a file download after this call if no other locks/transfers exist. It
does so by triggering the event ``dm.itemLocked``, which is intercepted by a
cache manager and forwarded to a transfer manager.

```
POST /dm/lock
```

Parameters:

```
sessionId=<string>
itemId=<string>
[ownerId=<string>]
```

The ``ownerId`` is optional and it defaults to the ``sessionId``. It is used
to keep track of who initiated the lock acquisition.

Example:

```
curl -X POST --header 'Content-Length: 0'\
    --header 'Content-Type: application/json'\
    --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/lock?sessionId=58d2d65dcbb11e24580bf6f2&itemId=58b08d98cbb11e6d0f95df9f'
```

Example response:

```json
{
    "_id": "58d2fd84cbb11e5639d7b1ae",
    "access": {
        "groups": [],
        "users": [{"id": "582f621ccbb11e75430a89ae", "level": 2}]
    },
    "itemId": "58b08d98cbb11e6d0f95df9f",
    "ownerId": "58d2d65dcbb11e24580bf6f2",
    "sessionId": "58d2d65dcbb11e24580bf6f2",
    "userId": "582f621ccbb11e75430a89ae"
}
```

#### List locks

Lists locks for a user, optionally filtering by ``sessionId``, ``itemId``,
and/or ``ownerId``.

```
GET /dm/lock
```

Parameters:

```
[sessionId=<string>]
[itemId=<string>]
[ownerId=<string>]
```

Alternate forms:

```
GET /dm/session/{id}/lock
```
(lists all locks for a user and session)


Example:

```
curl -X GET --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/lock'
```

Example response:

```json
[
    {
        "_accessLevel": 2,
        "_id": "58c9f3d0cbb11e4574dbf889",
        "_modelType": "lock",
        "itemId": "58b08d98cbb11e6d0f95df9f",
        "ownerId": "58c0924acbb11e3f338c865a",
        "sessionId": "58c0924acbb11e3f338c865a",
        "userId": "582f621ccbb11e75430a89ae"
    },
    ...
]
```

#### Get lock

Retrieves information about a lock

```
GET /dm/lock/{id}
```

Example:
```
curl -X GET --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/lock/58ca2594cbb11e63275eaf15'
```

Example response:
```json
{
    "_accessLevel": 2,
    "_id": "58ca2594cbb11e63275eaf15",
    "_modelType": "lock",
    "itemId": "58b08d98cbb11e6d0f95df9f",
    "ownerId": "58c0924acbb11e3f338c865a",
    "sessionId": "58c0924acbb11e3f338c865a",
    "userId": "582f621ccbb11e75430a89ae"
}
```

#### Release lock

Releases a lock. If no locks remain on the item that this lock belongs to,
then a ``dm.itemUnlocked`` event is triggered. This may, in turn, cause the
deletion of the file corresponding to the item from the cache.

```
DELETE /dm/lock/{id}
```

Example:

```
curl -X DELETE --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/lock/58ca2594cbb11e63275eaf15'
```

There is no response if the call succeeds.

### Transfers

The transfers collection keeps track of file transfers initiated by the DM.
The API is:

#### List transfers

```
GET /dm/transfer
```

Parameters:
```
[sessionId=<string>]
[discardOld=<"true"|"false">]
```

``sessionId`` can be used to only list transfers from a specific session. By
default, transfers finished more than 1 minute before this call is made are
not returned. To return all transfers, use ``discardOld=false``.

Example:
```
curl -X GET --header 'Accept: application/json'\
    --header 'Girder-Token: Mq359BMGKuxMCI0pM17gV1cPCEGWhtuFki83IlKKkIzZFZvSSNYhCkYElgtcpBQr'\
    'http://localhost:8080/api/v1/dm/transfer?discardOld=false&sessionId=58d2c9c7cbb11e1367df9ef7'
```

Example response:

```json
[
    {
        "_accessLevel": 2,
        "_id": "58d2ca45cbb11e1367df9efa",
        "_modelType": "transfer",
        "endTime": "Timestamp(1490209793, 1)",
        "error": null,
        "itemId": "58d2c427cbb11e0c17c7cc7e",
        "ownerId": "582f621ccbb11e75430a89ae",
        "path": "//Local/c",
        "sessionId": "58d2c9c7cbb11e1367df9ef7",
        "size": 1048576,
        "startTime": "Timestamp(1490209776, 4)",
        "status": 3,
        "transferred": 1048576
    }
    ...
]
```
The ``size`` and ``transferred`` fields can be used to calculate the
percentage of bytes transferred. The ``status`` field can have the following
values/meanings:
```
INITIALIZING = 0
QUEUED = 1
TRANSFERRING = 2
DONE = 3
FAILED = 4
```

A started transfer will have its ``startTime`` set to a UTC timestamp
representing the moment when the transfer was initiated. Similarly,
a finished transfer will have ``endTime`` set.
