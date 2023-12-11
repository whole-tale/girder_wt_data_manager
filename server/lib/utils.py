from girder.constants import SortDir
from girder.models.file import File
from girder.models.item import Item


def getLatestFile(item):
    """
    Given an item, return the latest file in the item.
    """
    files = list(
        Item().childFiles(
            item=item, limit=1, offset=0, sort=[("created", SortDir.DESCENDING)]
        )
    )
    try:
        return File().load(files[0]["_id"], force=True)
    except IndexError:
        raise Exception("No files found in item %s" % item["_id"])
