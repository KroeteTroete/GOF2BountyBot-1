import json, os


def readJSON(dbFile: str) -> dict:
    """Read the json file with the given path, and return the contents as a dictionary.

    :param str dbFile: Path to the file to read
    :return: The contents of the requested json file, parsed into a python dictionary
    :rtype: dict
    """
    with open(dbFile, "r") as f:
        data = json.load(f)
    return data


def writeJSON(dbFile: str, db: dict, prettyPrint=False):
    """Write the given json-serializable dictionary to the given file path.
    All objects in the dictionary must be JSON-serializable.

    :param str dbFile: Path to the file which db should be written to
    :param dict db: The json-serializable dictionary to write
    :param bool prettyPrint: When False, write minified JSON. When true, write JSON with basic pretty printing (indentation)
    """
    with open(dbFile, "w") as f:
        if prettyPrint:
            json.dump(db, f, indent=4, sort_keys=True)
        else:
            json.dump(db, f)


def saveDB(dbPath: str, db, **kwargs):
    """Call the given database object's toDict method, and save the resulting dictionary to the specified JSON file.
    TODO: child database classes to a single ABC, and type check to that ABC here before saving

    :param str dbPath: path to the JSON file to save to. Theoretically, this can be absolute or relative.
    :param db: the database object to save
    """
    writeJSON(dbPath, db.toDict(**kwargs))


async def saveDBAsync(dbPath: str, db, **kwargs):
    """This function should be used in place of saveDB for database objects whose toDict method is asynchronous.
    This function is currently unused.

    Await the given database object's toDict method, and save the resulting dictionary to the specified JSON file.
    TODO: child database classes to a single ABC, and type check to that ABC here before saving

    :param str dbPath: path to the JSON file to save to. Theoretically, this can be absolute or relative.
    :param db: the database object to save
    """
    writeJSON(dbPath, await db.toDict(**kwargs))


def depthLimitedWalk(top: str, maxDepth: int):
    """os.walk but with a limited recursion depth.
    Written by Kishan Patel:
    https://www.semicolonworld.com/question/57766/python-3-travel-directory-tree-with-limited-recursion-depth

    :param str top: Directory to start walking from
    :param int maxDepth: The maximum number of directories the walk will recurse into
    :return: An iterator in accordance with os.walk
    :rtype: Iterator
    """
    dirs, nondirs = [], []
    for name in os.listdir(top):
        (dirs if os.path.isdir(os.path.join(top, name)) else nondirs).append(name)
    yield top, dirs, nondirs
    if maxDepth > 1:
        for name in dirs:
            for x in depthLimitedWalk(os.path.join(top, name), maxDepth - 1):
                yield x
