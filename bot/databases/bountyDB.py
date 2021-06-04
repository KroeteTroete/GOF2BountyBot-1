from __future__ import annotations
from typing import Dict
from datetime import timedelta
from random import randint
import asyncio
import traceback

from ..gameObjects.bounties.criminal import Criminal
from typing import List
from ..baseClasses import serializable
from ..baseClasses.aliasableDict import AliasableDict
from ..cfg import cfg, bbData
from ..users import basedGuild, guildActivity
from .. import lib, botState
from ..scheduling.timedTask import TimedTask, DynamicRescheduleTask
from .bountyDivision import BountyDivision
from bot.gameObjects.bounties import bounty


def nameForDivision(div: BountyDivision) -> str:
    """Get the name for the given BountyDivision, as specified in cfg.bountyDivisions.

    :param BountyDivison div: The division to get the name of
    :return: The name for the given division
    :rtype: str
    :raise KeyError: When no name is found for the given division
    """
    try:
        return next(k for k, v in cfg.bountyDivisions.items() if div.minLevel == v[0])
    except KeyError:
        raise KeyError(f"The given division is non-standard, no name found: {div} range: {div.minLevel} - {div.maxLevel}")


class BountyDB(serializable.Serializable):
    """A database of Bounty.
    Bounty criminal names must be unique within the database.
    Faction names are case sensitive.

    :var divisions: Dictionary of tech level range to bounty division
    :vartype divisions: Dict[range, BountyDivision]
    :var owningBasedGuild: The BasedGuild where this DB's bounties are active
    :vartype owningBasedGuild: BasedGuild
    """

    def __init__(self, owningBasedGuild: "basedGuild.BasedGuild", dummy : bool = False):
        """
        :param BasedGuild owningBasedGuild: The guild that owns this bountyDB
        :param bool dummy: Whether this db is to be functional or only a placeholder (Default False)
        """
        if not dummy:
            self.divisions: Dict[range, BountyDivision] = {}
            for minLevel, maxLevel in cfg.bountyDivisions.values():
                self.divisions[range(minLevel, maxLevel+1)] = BountyDivision(self, minLevel, maxLevel)
            self.orderedDivs: List[BountyDivision] = []
            self.owningBasedGuild = owningBasedGuild


    def divisionForLevel(self, tl: int) -> BountyDivision:
        """Get the stored BountyDivision which handles bounties of the given level.

        :param int tl: The techlevel whose division to find
        :return: The BountyDivison responsible for bounties of the given level
        :rtype: BountyDivision
        :raise KeyError: When no division is found for bounties of the given level
        """
        try:
            return next(self.divisions[tlRange] for tlRange in self.divisions if tl in tlRange)
        except StopIteration:
            raise KeyError(f"No BountyDivision is registered for bounties of TL {tl}")


    def divisionForName(self, name: str) -> BountyDivision:
        """Get the stored BountyDivision for the given division name, as specified in cfg.bountyDivisions.

        :param str name: The name of the division to get
        :return: The BountyDivison of the given name
        :rtype: BountyDivision
        :raise KeyError: When no division is found for the given name
        """
        try:
            return self.divisionForLevel(cfg.bountyDivisions[name][0])
        except KeyError:
            raise KeyError(f"No BountyDivision with the given name: {name}")


    def clearAllBounties(self, includeEscaped=True):
        """Clear all bounties, for all factions in the DB

        :param bool includeEscaped: Whether to also clear escaped criminals (Default True)
        """
        for div in self.divisions.values():
            div.clear(includeEscaped=includeEscaped)


    async def resetAllNewBountyTTs(self):
        """Reset all new bounty TimedTasks, immediately triggering the spawning of one bounty per division
        """
        divTasks = set()
        for div in self.divisions.values():
            divTasks.add(asyncio.create_task(div.resetNewBountyCool()))
        if divTasks:
                await asyncio.wait(divTasks)
                for t in divTasks:
                    if e := t.exception():
                        botState.logger.log("bountyDB", "resetAllNewBountyTTs", str(e), category="bountiesDB",
                                            eventType=type(e).__name__, trace=traceback.format_exception(type(e), e, e.__traceback__))


    def getBountyByCrim(self, crim : Criminal, level : int = None) -> bounty.Bounty:
        """Get the bounty object for a given criminal name object
        This process is much more efficient when given the difficulty level of the criminal's bounty.

        :param Criminal crim: The criminal whose bounty is to be fetched.
        :param str level: The difficulty level of the criminal's bounty. Give None if this is not known,
                            to search all difficulties. (default None)

        :return: the bounty object tracking crim
        :rtype: Bounty
        :param int level: The difficulty level of the criminal's bounty, if known (Default None)
        :raise KeyError: If the requested criminal does not exist in this DB
        """
        # If the criminal's level is known
        if level is not None:
            try:
                return self.divisionForLevel(level).bounties[level][crim]
            except KeyError:
                pass

        # If the criminal's level is not known, search all levels
        else:
            for div in self.divisions.values():
                for tl in range(div.minLevel, div.maxLevel + 1):
                    try:
                        return div.bounties[tl][crim]
                    except KeyError:
                        pass
        
        raise KeyError(f"No bounty found for criminal: '{crim.name}'" + ("" if level is None else f" and level: {level}"))


    def getEscapedBountyByCrim(self, crim : Criminal, level : int = None) -> bounty.Bounty:
        """Get the escaped bounty object for a given criminal object.
        This process is much more efficient when given the difficulty level of the criminal's bounty.

        :param Criminal crim: The criminal whose escaped bounty is to be fetched.
        :param str level: The difficulty level of the criminal's bounty. Give None if this is not known,
                            to search all difficulties. (default None)

        :return: the escaped bounty object tracking crim
        :rtype: Bounty
        :param int level: The difficulty level of the criminal's bounty, if known (Default None)
        :raise KeyError: If the requested criminal does not exist in this DB
        """
        # If the criminal's level is known
        if level is not None:
            try:
                return self.divisionForLevel(level).escapedBounties[level][crim]
            except KeyError:
                pass

        # If the criminal's level is not known, search all levels
        else:
            for div in self.divisions.values():
                for tl in range(div.minLevel, div.maxLevel + 1):
                    try:
                        return div.escapedBounties[tl][crim]
                    except KeyError:
                        pass
        
        raise KeyError(f"No escaped bounty found for criminal: '{crim.name}'" + ("" if level is None else f" and level: {level}"))


    def getBounty(self, name : str, level : int = None) -> bounty.Bounty:
        """Get the bounty object for a given criminal name or alias.
        This process is much more efficient when given the difficulty level of the criminal's bounty.

        :param str name: A name or alias for the criminal whose bounty is to be fetched.
        :param str level: The difficulty level of the criminal's bounty. Give None if this is not known,
                            to search all difficulties. (default None)

        :return: the bounty object tracking the named criminal
        :rtype: Bounty
        :param int level: The difficulty level of the criminal's bounty, if known (Default None)
        :raise KeyError: If the requested criminal name does not exist in this DB
        """
        # If the criminal's level is known
        if level is not None:
            return self.divisionForLevel(level).bounties[level].getValueForKeyNamed(name)

        # If the criminal's level is not known, search all levels
        else:
            for div in self.divisions.values():
                for tl in range(div.minLevel, div.maxLevel + 1):
                    try:
                        return div.bounties[tl].getValueForKeyNamed(name)
                    except KeyError:
                        pass
        
        raise KeyError("No bounty found for name: '" + name + ("'" if level is None else "' and level: " + str(level)))


    def getEscapedBounty(self, name : str, level : int = None) -> bounty.Bounty:
        """Get the escaped bounty object for a given criminal name or alias.
        This process is much more efficient when given the difficulty level of the criminal's bounty.

        :param str name: A name or alias for the criminal whose escaped bounty is to be fetched.
        :param str level: The difficulty level of the criminal's bounty. Give None if this is not known,
                            to search all difficulties. (default None)

        :return: the escaped bounty object tracking the named criminal
        :rtype: Bounty
        :param int level: The difficulty level of the criminal's bounty, if known (Default None)
        :raise KeyError: If the requested criminal name does not exist in this DB
        """
        # If the criminal's level is known
        if level is not None:
            return self.divisionForLevel(level).escapedBounties[level].getValueForKeyNamed(name)

        # If the criminal's level is not known, search all levels
        else:
            for div in self.divisions.values():
                for tl in range(div.minLevel, div.maxLevel + 1):
                    try:
                        return div.escapedBounties[tl].getValueForKeyNamed(name)
                    except KeyError:
                        pass
        
        raise KeyError(f"No escaped bounty found for name: '{name}'" + ("" if level is None else " and level: " + str(level)))


    def totalBounties(self, includeEscaped : bool = True) -> int:
        """Decide the total number of bounties currently stored across all divisions.
        If includeEscaped is given as true, escaped bounties will also be counted.

        :param bool includeEscaped: Whether or not to count escaped bounties as well as active bounties (Default True)
        :return: The number of bounties stored in the DB across all divisions
        :rtype: int
        """
        return sum(div.getNumBounties(includeEscaped=includeEscaped) for div in self.divisions)


    def canMakeBounty(self) -> bounty.Bounty:
        """Check whether this DB has space for more bounties

        :return: True if at least one division is not at capacity, False if all divisions' bounties are full
        :rtype: bool
        """
        return any(not div.isFull() for div in self.divisions.values())


    def bountyNameExists(self, name : str, level : int = None, noEscapedCrim : bool = True) -> bool:
        """Check whether a criminal with the given name or alias exists in the DB
        The process is much more efficient if the faction where the criminal should reside is known.

        :param str name: The name or alias to check for criminal existence against
        :param str level: The difficulty level of the named criminal's bounty.
                            Use None if the level is not known. (default None)
        :param bool noEscapedCrim: When False, the escaped criminals database is also checked (default True)

        :return: True if a bounty is found for a criminal with the given name,
                    False if the given name does not correspond to an active bounty in this DB
        :rtype: bool
        """
        # Search for a bounty object under the given name
        try:
            self.getBounty(name, level)
        # Return False if the name was not found, True otherwise
        except KeyError:
            if not noEscapedCrim:
                try:
                    self.getEscapedBounty(name, level)
                except KeyError:
                    return False
            else:
                return False
        return True
    

    def divisionObjExists(self, div: BountyDivision) -> bool:
        """Decide whether this DB owns the given division.

        :param BountyDivision div: The division to check for ownership
        :return: True if div is one of this DB's divisions, False otherwise
        :rtype: bool
        """
        return div in self.divisions.values()


    def bountyObjExists(self, bounty : bounty.Bounty) -> bool:
        """Check whether a given bounty object exists in the DB.
        Existence is checked for the bounty's criminal, at the given techLevel

        :param Bounty bounty: The bounty object to check for existence in the DB
        :return: True if the given bounty's criminal is in the DB at the given techLevel, False otherwise
        :rtype: bool
        """
        return self.divisionForLevel(bounty.techLevel).bountyObjExists(bounty)


    def criminalObjExists(self, crim : Criminal) -> bool:
        """Check whether a given criminal object exists in the DB.
        Existence is checked across all divisions and levels.

        :param Criminal crim: The criminal object to check for existence in the DB
        :return: True if the given criminal is found within the DB, False otherwise
        :rtype: bool
        """
        return any(div.criminalObjExists(crim) for div in self.divisions.values())


    def addBounty(self, bounty : bounty.Bounty):
        """Add a given bounty object to the database.
        Bounties cannot be added if the division for its level does not have space for more bounties.
        Bounties cannot be added if a bounty already exists for the same criminal in this DB.

        :param Bounty bounty: the bounty object to add to the database
        :raise OverflowError: if the division for this bounty's level is already at capacity
        :raise ValueError: if the criminal is already wanted in the database
        """
        div = self.divisionForLevel(bounty.techLevel)

        # Ensure the DB has space for the bounty
        if div.isFull(includeEscaped=True):
            raise OverflowError(f"Division for the bounty ({bounty.criminal.name}, level {bounty.techLevel}) is full")
        
        if self.criminalObjExists(bounty.criminal):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already wanted: {bounty.criminal} by {bounty}")

        # # ensure the given bounty does not already exist
        # if self.bountyNameExists(bounty.criminal.name, noEscapedCrim=False):
        #     raise ValueError("Attempted to add a bounty whose name already exists: " + bounty.criminal.name)

        # Add the bounty to the database
        div.bounties[bounty.techLevel][bounty.criminal] = bounty
        if div.latestBounty is None or bounty.issueTime > div.latestBounty.issueTime:
            div.latestBounty = bounty


    def escapedCriminalExists(self, crim):
        """Decide whether a criminal is recorded in the escaped criminals database.

        :param criminal crim: The criminal to check for existence
        :return: True if crim is in this database's escaped criminals record, False otherwise
        :rtype: bool
        """
        return any(div.escapedCriminalExists(crim) for div in self.divisions.values())


    def addEscapedBounty(self, bounty : bounty.Bounty):
        """Add a given bounty object to the escaped bounties database.
        Bounties cannot be added if the object or name already exists in the database.

        :param Bounty bounty: the bounty object to add to the database
        :raise ValueError: if the requested bounty's name already exists in the database
        """
        div = self.divisionForLevel(bounty.techLevel)

        # Ensure the DB has space for the bounty
        if div.isFull(includeEscaped=True):
            raise OverflowError(f"Division for the escaped bounty ({bounty.criminal.name}, level {bounty.techLevel}) is full")
        
        if self.criminalObjExists(bounty.criminal):
            raise ValueError(f"Attempted to add escaped {bounty} for a criminal who is already wanted: " \
                            + f"{bounty.criminal} by unescaped {bounty}")
        if self.escapedCriminalExists(bounty.criminal):
            raise ValueError(f"Attempted to add escaped {bounty} for a criminal who is already wanted: " \
                            + f"{bounty.criminal} by escaped {bounty}")
        # # ensure the given bounty does not already exist
        # if self.bountyNameExists(bounty.criminal.name, noEscapedCrim=False):
        #     raise ValueError("Attempted to add a bounty whose name already exists: " + bounty.criminal.name)

        # Add the bounty to the database
        div.escapedBounties[bounty.techLevel][bounty.criminal] = bounty


    def removeEscapedCriminal(self, crim):
        """Remove a criminal from the record of escaped criminals.
        crim must already be recorded in the escaped criminals database.
        This does not perform respawning of the bounty.

        :param criminal crim: The criminal to remove from the record
        :raise KeyError: If criminal is not registered in the db
        """
        try:
            bounty = self.getEscapedBountyByCrim(crim)
        except KeyError:
            raise KeyError("Escaped criminal not found: " + crim.name)
        else:
            del self.divisionForLevel(bounty.techLevel).escapedBounties[bounty.techLevel][bounty.criminal]
            # print(f"removed escaped criminal {bounty.criminal.name} from div {nameForDivision(self.divisionForLevel(bounty.techLevel))}, level {bounty.techLevel}")


    def removeBountyObj(self, bounty : bounty.Bounty):
        """Remove a given bounty object from the database.

        :param Bounty bounty: the bounty object to remove from the database
        """
        try:
            del self.divisionForLevel(bounty.techLevel).bounties[bounty.techLevel][bounty.criminal]
        except KeyError:
            raise KeyError("Bounty not found: " + bounty.criminal.name)


    def removeBountyName(self, name : str, faction : str = None):
        """Find the bounty associated with the given criminal name or alias, and remove it from the database.
        This process is much more efficient if the faction under which the bounty is wanted is given.

        :param str name: The name of the criminal to remove
        :param str faction: The faction whose bounties to check for the named criminal.
                            Use None if the faction is not known. (default None)
        """
        self.removeBountyObj(self.getBounty(name, faction=faction))


    def hasBounties(self) -> bool:
        """Check whether any division has bounties stored.

        :return: True if at least one bounty is stored in this DB, False otherwise
        :rtype: bool
        """
        return any(not div.isEmpty() for div in self.divisions.values())


    def toDict(self, **kwargs) -> dict:
        """Serialise the bountyDB and all of its divisions into dictionary format.

        :return: A dictionary containing all data needed to recreate this bountyDB.
        :rtype: dict
        """
        data = {"active": [], "escaped": [], "temperatures": {}}
        for div in self.divisions.values():
            data["temperatures"][div.minLevel] = div.temperature
            for tlBounties in div.bounties.values():
                for bty in tlBounties.values():
                    data["active"].append(bty.toDict(**kwargs))
            for tlBounties in div.escapedBounties.values():
                for bty in tlBounties.values():
                    data["escaped"].append(bty.toDict(**kwargs))

        return data


    @classmethod
    def fromDict(cls, bountyDBDict: dict, owningBasedGuild: basedGuild.BasedGuild = None, dbReload: bool = False, **kwargs) -> BountyDB:
        """Build a bountyDB object from a serialised dictionary format - the reverse of bountyDB.toDict.

        :param dict bountyDBDict: a dictionary representation of the bountyDB, to convert to an object
        :param bool dbReload: Whether or not this bountyDB is being created during the initial database loading
                                phase of bountybot. This is used to toggle name checking in bounty contruction.
        :param basedGuild.BasedGuild owningBasedGuild: The guild that owns this bountyDB. Required argument.
        :return: The new bountyDB object
        :rtype: bountyDB
        """
        if owningBasedGuild is None:
            raise ValueError("missing required kwarg: owningBasedGuild")

        escapedBountiesData = bountyDBDict.get("escaped", [])
        activeBountiesData = bountyDBDict.get("active", [])
        temps = bountyDBDict.get("temperatures", {})

        # Instanciate a new bountyDB
        newDB = BountyDB(owningBasedGuild)

        for minLevel, divTemp in temps.items():
            newDB.divisionForLevel(int(minLevel)).temperature = divTemp

        for bountyDict in activeBountiesData:
            newDB.addBounty(bounty.Bounty.fromDict(bountyDict, dbReload=dbReload, owningDB=newDB))
        for bountyDict in escapedBountiesData:
            # Adding escaped bounties to DB is done during Bounty.fromDict
            bounty.Bounty.fromDict(bountyDict, dbReload=dbReload, owningDB=newDB)

        return newDB
