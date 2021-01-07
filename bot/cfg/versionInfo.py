import os
from . import cfg
from .. import lib
from datetime import datetime
from typing import Dict, Union
import re
import aiohttp

# Path to the BASED version json descriptor file. File also contains the timestamp of the next scheduled version check.
BASED_VERSIONFILE = 'bot/cfg/version/BASED_version.json'
# Pointer to the BASED repository. Do not change this.
BASED_REPO_URL = "https://github.com/Trimatix/BASED/"
BASED_API_URL = "https://api.github.com/repos/" + "/".join(BASED_REPO_URL.split("/")[-3:-1]) + "/releases"


class UpdatesCheckFailed(Exception):
    pass


class UpdateCheckResults:
    """Data class representing the results of a bot version check.

    :var updatesChecked: whether or not an updates check was attempted
    :vartype updatesChecked: bool
    :var latestVersion: String name of the latest version
    :vartype latestVersion: str
    :var upToDate: Whether or not the current bot version is latestVersion
    :vartype upToDate: bool
    """
    def __init__(self, updatesChecked : bool, latestVersion : str = None, upToDate : bool = None):
        """Data class representing the results of a bot version check.

        :param bool updatesChecked: whether or not an updates check was attempted
        :param str latestVersion: String name of the latest version. None when updatesChecked is False
        :param bool upToDate: Whether or not the current bot version is latestVersion. None when updatesChecked is False
        """
        self.updatesChecked = updatesChecked
        self.latestVersion = latestVersion
        self.upToDate = upToDate


def getBASEDVersion() -> Dict[str, Union[str, float]]:
    """Get info about the running BASED version, from file.

    :return: A dictionary describing the current BASED version, and the next scheduled updates check.
    :rtype: dict[string, string or float]
    """
    # Ensure file existence
    if not os.path.isfile(BASED_VERSIONFILE):
        raise RuntimeError("BASED version file not found, please update cfg.versionInfo.BASED_VERSIONFILE path")
    # Read version file
    return lib.jsonHandler.readJSON(BASED_VERSIONFILE)


async def getNewestTagOnRemote(httpClient : aiohttp.ClientSession, url : str) -> str:
    """Fetch the name of the latest tag on the given git remote.
    If the remote has no tags, empty string is returned.
    Python port of lukechild's shell gist: https://gist.github.com/lukechilds/a83e1d7127b78fef38c2914c4ececc3c

    :param aiohttp.ClientSession httpClient: The ClientSession to request git info with
    :param str url: URL to the git remote to check
    :return: String name of the the latest tag on the remote at URL, if the remote at URL has any tags. Empty string otherwise
    :rtype: str 
    """
    async with httpClient.get(url) as resp:
        if not resp.ok:
            raise UpdatesCheckFailed()
        try:
            respJSON = await resp.json()
            return respJSON[0]["tag_name"]
        except (IndexError, KeyError, aiohttp.ContentTypeError):
            raise UpdatesCheckFailed()


# Version of BASED currently installed
BASED_VERSION = getBASEDVersion()["BASED_version"]


async def checkForUpdates(httpClient : aiohttp.ClientSession) -> UpdateCheckResults:
    """Check the BASED repository for new releases.
    Could be easily extended to check your own bot repository for updates as well.

    :param aiohttp.ClientSession httpClient: The ClientSession to request git info with
    :return: The latest BASED version and whether or not this installation is up to date, if the scheduled check time has been reached. UpdateCheckResults indicating that no check was performed otherwise.
    :rtype: UpdateCheckResults
    """
    # Fetch the next scheduled updates check from file
    nextUpdateCheck = datetime.utcfromtimestamp(getBASEDVersion()["next_update_check"])

    # Is it time to check yet?
    if datetime.utcnow() >= nextUpdateCheck:
        # Get latest version
        latest = await getNewestTagOnRemote(httpClient, BASED_API_URL)

        # Schedule next updates check
        nextCheck = datetime.utcnow() + lib.timeUtil.timeDeltaFromDict(cfg.BASED_updateCheckFrequency)
        lib.jsonHandler.writeJSON(BASED_VERSIONFILE,
                                    {   "BASED_version"     : BASED_VERSION,
                                        "next_update_check" : nextCheck.timestamp()})
        
        # If no tags were found on remote, assume up to date.
        upToDate = (latest == BASED_VERSION) if latest else True
        return UpdateCheckResults(True, latestVersion=latest, upToDate=upToDate)

    # If not time to check yet, indicate as such
    return UpdateCheckResults(False)
    
