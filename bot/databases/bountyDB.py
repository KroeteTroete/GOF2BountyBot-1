from __future__ import annotations
from bot.cfg import bbData
from typing import Dict
from datetime import timedelta
from random import randint

from ..gameObjects.bounties import bounty, criminal
from ..gameObjects.bounties.bountyConfig import BountyConfig
from typing import List
from ..baseClasses import serializable
from ..baseClasses.aliasableDict import AliasableDict
from ..cfg import cfg
from ..users import basedGuild, guildActivity
from .. import lib, botState
from ..scheduling.timedTask import TimedTask, DynamicRescheduleTask


class BountyDB(serializable.Serializable):
    """A database of bbObject.bounties.bounty.
    Bounty criminal names and faction names must be unique within the database.
    Faction names are case sensitive.

    TODO: Give factions default values

    :var bounties: Dictionary of faction name to list of bounties
    :vartype bounties: dict
    :var factions: List of str faction names, to be used in self.bounties keys
    :vartype factions: list
    :var latestBounty: The most recent bounty to be added to this db.As of writing,
                        this is only used when scaling new bounty delays by the most recent length
    :vartype latestBounty: gameObjects.bounties.bounty.Bounty
    """

    def __init__(self, owningBasedGuild: "basedGuild.BasedGuild",
                    activityMonitor: guildActivity.ActivityMonitor = None, dummy = False):
        """
        :param List[str] factions: list of unique faction names useable in this db's bounties
        :param BasedGuild owningBasedGuild: The guild that owns this bountyDB
        """
        self.owningBasedGuild = owningBasedGuild
        self.activityMonitor = activityMonitor or guildActivity.ActivityMonitor()

        bountyDelayGenerators = {"random": lib.timeUtil.getRandomDelaySeconds,
                                "fixed-routeScale": self.getRouteScaledBountyDelayFixed,
                                "random-routeScale": self.getRouteScaledBountyDelayRandom,
                                "random-routeScale-tempScale": self.getRouteTempScaledBountyDelayRandom}

        bountyDelayGeneratorArgs = {"random": cfg.newBountyDelayRandomRange,
                                    "fixed-routeScale": cfg.newBountyFixedDelta,
                                    "random-routeScale": cfg.newBountyDelayRandomRange,
                                    "random-routeScale-tempScale": cfg.newBountyDelayRandomRange}

        self.maxBounties: List[int] = [1] * guildActivity._numTLs
        self.newBountyTTs: List[TimedTask] = [None] * guildActivity._numTLs
        self.latestBounties: List[bounty.Bounty] = [None] * guildActivity._numTLs

        for tl in guildActivity._tlsRange:
            # linear temperature-maxBounty scaling
            self.maxBounties[tl] = min(int(self.activityMonitor.temperatures[tl]), cfg.maxBountiesPerFaction)

        if not dummy:
            if cfg.newBountyDelayType == "fixed":
                self.newBountyTTs = [TimedTask(expiryDelta=lib.timeUtil.timeDeltaFromDict(cfg.newBountyFixedDelta),
                                                autoReschedule=True, expiryFunction=owningBasedGuild.spawnAndAnnounceBounty,
                                                expiryFunctionArgs={"newBounty": None,
                                                                    "newConfig": BountyConfig(techLevel=tl)}) \
                                                                                    for tl in guildActivity._tlsRange]
            else:
                for tl in guildActivity._tlsRange:
                    try:
                        delayGenerator = bountyDelayGenerators[cfg.newBountyDelayType]
                        generatorArgs = [bountyDelayGeneratorArgs[cfg.newBountyDelayType], tl]
                    except KeyError:
                        raise ValueError("cfg: Unrecognised newBountyDelayType '" + cfg.newBountyDelayType + "'")
                    else:
                        self.newBountyTTs[tl] = DynamicRescheduleTask(delayGenerator,
                                                                        delayTimeGeneratorArgs=generatorArgs,
                                                                        autoReschedule=True,
                                                                        expiryFunction=owningBasedGuild.spawnAndAnnounceBounty,
                                                                        expiryFunctionArgs={"newBounty": None, \
                                                                                        "newConfig": BountyConfig(techLevel=tl)})

            for tt in self.newBountyTTs:
                botState.taskScheduler.scheduleTask(tt)


    def getRouteScaledBountyDelayFixed(self, data: List[Dict[str, int], int]) -> timedelta:
        """New bounty delay generator, scaling a fixed delay by the length of the presently spawned bounty.

        :param dict baseDelayDict: A lib.timeUtil.timeDeltaFromDict-compliant dictionary describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A datetime.timedelta indicating the time to wait before spawning a new bounty
        :rtype: datetime.timedelta
        """
        baseDelayDict, tl = data
        timeScale = cfg.fallbackRouteScale if self.latestBounties[tl] is None else \
                    len(self.latestBounties[tl].route)
        delay = lib.timeUtil.timeDeltaFromDict(baseDelayDict) * timeScale * cfg.newBountyDelayRouteScaleCoefficient
        botState.logger.log("Main", "routeScaleBntyDelayFixed",
                            "New bounty delay generated, " \
                                + ("no latest criminal." if self.latestBounties[tl] is None else \
                                + ("latest criminal: '" + self.latestBounties[tl].criminal.name + "'. Route Length " \
                                + str(len(self.latestBounties[tl].route)))) + "\nDelay picked: " + str(delay),
                            category="newBounties",
                            eventType="NONE_BTY" if self.latestBounties[tl] is None else "DELAY_GEN", noPrint=True)
        return delay


    def getRouteScaledBountyDelayRandom(self, data: List[Dict[str, int], int]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty.

        :param dict baseDelayDict: A dictionary describing the minimum and maximum time in seconds to wait after a bounty is
                                    spawned with route length 1
        :return: A datetime.timedelta indicating the time to wait before spawning a new bounty
        :rtype: datetime.timedelta
        """
        baseDelayDict, tl = data
        timeScale = cfg.fallbackRouteScale if self.latestBounties[tl] is None else \
                    len(self.latestBounties[tl].route)
        delay = lib.timeUtil.getRandomDelaySeconds({"min": baseDelayDict["min"] * timeScale \
                                                        * cfg.newBountyDelayRouteScaleCoefficient,
                                                    "max": baseDelayDict["max"] * timeScale \
                                                        * cfg.newBountyDelayRouteScaleCoefficient})
        botState.logger.log("Main", "routeScaleBntyDelayRand",
                            "New bounty delay generated, " \
                                + ("no latest criminal." if self.latestBounties[tl] is None else \
                                    ("latest criminal: '" + self.latestBounties[tl].criminal.name \
                                + "'. Route Length " + str(len(self.latestBounties[tl].route)))) + "\nRange: " \
                                + str((baseDelayDict["min"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60) \
                                + "m - " \
                                + str((baseDelayDict["max"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60) \
                                + "m\nDelay picked: " + str(delay), category="newBounties",
                            eventType="NONE_BTY" if self.latestBounties[tl] is None else "DELAY_GEN", noPrint=True)
        return delay


    def getRouteTempScaledBountyDelayRandom(self, data: List[Dict[str, int], int]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty and the current activity temperature at the
        presently spawned bounty's tech level.

        :param dict baseDelayDict: A dictionary describing the minimum and maximum time in seconds to wait after a bounty is
                                    spawned with route length 1
        :return: A datetime.timedelta indicating the time to wait before spawning a new bounty
        :rtype: datetime.timedelta
        """
        baseDelayDict, tl = data
        timeScale = cfg.fallbackRouteScale if self.latestBounties[tl] is None else \
                    len(self.latestBounties[tl].route)
        tempScale = self.activityMonitor.measureTL(tl) ** - 0.1
        numSeconds = randint(baseDelayDict["min"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient,
                            baseDelayDict["max"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient)
        delay = timedelta(seconds=tempScale * numSeconds)
        botState.logger.log("Main", "routeTempScaleBntyDelayRand",
                            "New bounty delay generated, " \
                                + "temp " + str(self.activityMonitor.measureTL(tl)) + " -> scale " + str(round(tempScale, 2))
                                + (" no latest criminal." if self.latestBounties[tl] is None else \
                                    (" latest criminal: '" + self.latestBounties[tl].criminal.name \
                                + "'. Route Length " + str(len(self.latestBounties[tl].route)))) + "\nRange: " \
                                + str((baseDelayDict["min"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60) \
                                + "m - " \
                                + str((baseDelayDict["max"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60) \
                                + "m\nPre-temp scale: " + lib.timeUtil.td_format_noYM(timedelta(seconds=numSeconds))
                                + "\nDelay picked: " + lib.timeUtil.td_format_noYM(delay), category="newBounties",
                            eventType="NONE_BTY" if self.latestBounties[tl] is None else "DELAY_GEN", noPrint=True)
        return delay


    def getFactions(self) -> List[bounty.Bounty]:
        """Get the list of useable faction names for this DB

        :return: A list containing this DB's useable faction names
        :rtype: list
        """
        return self.bounties.keys()


    def getFactionBounties(self, faction : str) -> List[bounty.Bounty]:
        """Get a list of all bounty objects stored under a given faction.

        :param str faction: The faction whose bounties to return. Case sensitive.
        :return: A list containing references to all bounties made available by faction.
        :rtype: ValuesView
        """
        return self.bounties[faction].values()

    
    def factionExists(self, faction : str) -> bool:
        """Decide whether a given faction name is useable in this DB

        :param str faction: The faction to test for existence. Case sensitive.

        :return: True if faction is one of this DB's factions, false otherwise.
        :rtype: bool
        """
        return faction in self.getFactions()


    def addFaction(self, faction: str):
        """Add a new useable faction name to the DB

        :param str faction: The new name to enable bounty storage under. Must be unique within the db.
        :raise KeyError: When attempting to add a faction which already exists in this DB
        """
        # Ensure faction name does not already exist
        if self.factionExists(faction):
            raise KeyError("Attempted to add a faction that already exists: " + faction)
        # Initialise faction's database to empty
        self.bounties[faction] = AliasableDict()
        self.escapedBounties[faction] = AliasableDict()


    def removeFaction(self, faction: str):
        """Remove a faction name from this DB

        :param str faction: The faction name to remove. Case sensitive.
        :raise KeyError: When given a faction which does not exist in this DB
        """
        # Ensure the faction name exists
        if not self.factionExists(faction):
            raise KeyError("Unrecognised faction: " + faction)
        # Remove the faction name from the DB
        del self.bounties[faction]
        del self.escapedBounties[faction]


    def clearFactionBounties(self, faction: str):
        """Clear all bounties stored under a given faction

        :param str faction: The faction whose bounties to clear
        :raise KeyError: When given a faction which does not exist in this DB
        """
        # Ensure the faction name exists
        if not self.factionExists(faction):
            raise KeyError("Unrecognised faction: " + faction)
        # Remove latest bounty if they are in this faction
        for tl in guildActivity._tlsRange:
            if self.latestBounties[tl] is not None and self.latestBounties[tl].faction == faction:
                self.latestBounties[tl] = None
        # Empty the faction's bounties
        self.bounties[faction] = AliasableDict()
        self.escapedBounties[faction] = AliasableDict()


    def clearAllBounties(self):
        """Clear all bounties, for all factions in the DB
        """
        for fac in self.getFactions():
            self.clearFactionBounties(fac)


    def getFactionNumBounties(self, faction : str) -> int:
        """Get the number of bounties stored by a faction.

        :param str faction: The faction whose bounties to return. Case sensitive.

        :return: Integer number of bounties stored by a faction
        :rtype: int
        """
        return len(self.getFactionBounties(faction))


    def getBounty(self, name : str, faction : str = None) -> bounty.Bounty:
        """Get the bounty object for a given criminal name or alias.
        This process is much more efficient when given the faction that the criminal is wanted by.

        :param str name: A name or alias for the criminal whose bounty is to be fetched.
        :param str faction: The faction by which the criminal is wanted. Give None if this is not known,
                            to search all factions. (default None)

        :return: the bounty object tracking the named criminal
        :rtype: Bounty

        :raise KeyError: If the requested criminal name does not exist in this DB
        """
        # If the criminal's faction is known
        if faction is not None:
            return self.bounties[faction].getValueForKeyNamed(name)

        # If the criminal's faction is not known, search all factions
        else:
            for fac in self.getFactions():
                try:
                    return self.bounties[fac].getValueForKeyNamed(name)
                except KeyError:
                    pass
        
        raise KeyError("No bounty found for name: '" + name + ("'" if not faction else "' and faction: " + faction))


    def getEscapedCriminal(self, name: str, faction : str = None) -> criminal.Criminal:
        """Get the criminal object for a given name or alias, from the list of escaped criminals.
        This process is much more efficient when given the faction that the criminal is wanted by.

        :param str name: A name or alias for the criminal to be fetched.
        :param str faction: The faction by which the criminal is wanted.
                            Give None if this is not known, to search all factions. (Default None)
        :return: The named criminal
        :rtype: str
        :throws KeyError: If the requested criminal name does not exist in the escapedCriminals list
        """
        # If the criminal's faction is known
        if faction is not None:
            return self.escapedBounties[faction].getKeyNamed(name)

        # If the criminal's faction is not known, search all factions
        else:
            for fac in self.getFactions():
                try:
                    return self.escapedBounties[fac].getKeyNamed(name)
                except KeyError:
                    pass

        # The criminal was not recognised, raise an error
        raise KeyError("Bounty not found: " + name)


    def factionCanMakeBounty(self, faction : str) -> bool:
        """Check whether a faction has space for more bounties

        :param str faction: the faction whose DB space to check

        :return: True if the requested faction has space for more bounties, False otherwise
        :rtype: bool
        """
        return self.getFactionNumBounties(faction) < cfg.maxBountiesPerFaction


    def canMakeBounty(self) -> bounty.Bounty:
        """Check whether this DB has space for more bounties

        :return: True if at least one faction is not at capacity, False if all factions' bounties are full
        :rtype: bool
        """
        # Check all bounties for factionCanMakeBounty
        for fac in self.getFactions():
            if self.factionCanMakeBounty(fac):
                # If a faction can take a bounty, return True
                return True

        # No faction found with space remaining
        return False


    def bountyNameExists(self, name : str, faction : str = None, noEscapedCrim : bool = True) -> bool:
        """Check whether a criminal with the given name or alias exists in the DB
        The process is much more efficient if the faction where the criminal should reside is known.

        :param str name: The name or alias to check for criminal existence against
        :param str faction: The faction whose bounties to check for the named criminal.
                            Use None if the faction is not known. (default None)
        :param bool noEscapedCrim: When False, the escaped criminals database is also checked (default True)

        :return: True if a bounty is found for a criminal with the given name,
                    False if the given name does not correspond to an active bounty in this DB
        :rtype: bool
        """
        # Search for a bounty object under the given name
        try:
            self.getBounty(name, faction)
        # Return False if the name was not found, True otherwise
        except KeyError:
            if not noEscapedCrim:
                try:
                    self.getEscapedCriminal(name, faction)
                except KeyError:
                    return False
            else:
                return False
        return True


    def bountyObjExists(self, bounty : bounty.Bounty) -> bool:
        """Check whether a given bounty object exists in the DB.
        Existence is checked by the bounty __eq__ method, which is currently object equality
        (i.e physical memory address equality)

        :param bounty.Bounty bounty: The bounty object to check for existence in the DB
        :return: True if the given bounty is found within the DB, False otherwise
        :rtype: bool
        """
        return bounty in self.getFactionBounties(bounty.faction)


    def addBounty(self, bounty : bounty.Bounty):
        """Add a given bounty object to the database.
        Bounties cannot be added if the bounty.faction does not have space for more bounties.
        Bounties cannot be added if the object or name already exists in the database.

        :param bounty.Bounty bounty: the bounty object to add to the database
        :raise OverflowError: if the bounty.faction does not have space for more bounties
        :raise ValueError: if the requested bounty's name already exists in the database
        """
        # Ensure the DB has space for the bounty
        if not self.factionCanMakeBounty(bounty.faction):
            raise OverflowError("Requested faction's bounty DB is full")

        # ensure the given bounty does not already exist
        if self.bountyNameExists(bounty.criminal.name, noEscapedCrim=False):
            raise ValueError("Attempted to add a bounty whose name already exists: " + bounty.criminal.name)

        # Add the bounty to the database
        self.bounties[bounty.faction][bounty.criminal] = bounty
        self.latestBounties[bounty.techLevel] = bounty


    def escapedCriminalExists(self, crim):
        """Decide whether a criminal is recorded in the escaped criminals database.
        :param criminal crim: The criminal to check for existence
        :return: True if crim is in this database's escaped criminals record, False otherwise
        :rtype: bool
        """
        return crim in self.escapedBounties[crim.faction]


    def addEscapedBounty(self, bounty : bounty.Bounty):
        """Add a given bounty object to the escaped bounties database.
        Bounties cannot be added if the object or name already exists in the database.

        :param bounty.Bounty bounty: the bounty object to add to the database
        :raise ValueError: if the requested bounty's name already exists in the database
        """
        # ensure the given bounty does not already exist
        if self.bountyNameExists(bounty.criminal.name) or self.escapedCriminalExists(bounty.criminal):
            raise ValueError("Attempted to add a bounty whose name already exists: " + bounty.criminal.name)

        # Add the bounty to the database
        self.escapedBounties[bounty.faction][bounty.criminal] = bounty


    def removeEscapedCriminal(self, crim):
        """Remove a criminal from the record of escaped criminals.
        crim must already be recorded in the escaped criminals database.
        This does not perform respawning of the bounty.

        :param criminal crim: The criminal to remove from the record
        :raise KeyError: If criminal is not registered in the db
        """
        if not self.escapedCriminalExists(crim):
            raise KeyError("criminal not found: " + crim.name)
        del self.escapedBounties[crim.faction][crim]


    def removeBountyObj(self, bounty : bounty.Bounty):
        """Remove a given bounty object from the database.

        :param bounty.Bounty bounty: the bounty object to remove from the database
        """
        if bounty is self.latestBounties[bounty.techLevel]:
            self.latestBounties[bounty.techLevel] = None
        if not self.bountyObjExists(bounty):
            raise KeyError("criminal not found: " + bounty.criminal.name)
        del self.bounties[bounty.faction][bounty.criminal]


    def removeBountyName(self, name : str, faction : str = None):
        """Find the bounty associated with the given criminal name or alias, and remove it from the database.
        This process is much more efficient if the faction under which the bounty is wanted is given.

        :param str name: The name of the criminal to remove
        :param str faction: The faction whose bounties to check for the named criminal.
                            Use None if the faction is not known. (default None)
        """
        self.removeBountyObj(self.getBounty(name, faction=faction))


    def hasBounties(self, faction : str = None) -> bool:
        """Check whether the given faction has any bounties stored, or if ANY faction has bounties stored if none is given.

        :param str faction: The faction whose bounties to check. Give None to check all factions for bounties. (default None)
        :return: True if at least one bounty is stored in this DB, False otherwise
        :rtype: bool
        """
        # If no faction is specified
        if faction is None:
            # Return true if any faction has at least one bounty
            for fac in self.getFactions():
                if self.getFactionNumBounties(fac) != 0:
                    return True
            # no bounties found, return false
            return False

        # If a faction is specified, return true if it has at least one bounty
        else:
            return self.getFactionNumBounties(faction) != 0


    def __str__(self) -> str:
        """Return summarising info about this bountyDB in string format.
        Currently: The number of factions in the DB.

        :return: a string summarising this db
        :rtype: str
        """
        return "<bountyDB: " + str(len(self.bounties)) + " factions>"


    def toDict(self, **kwargs) -> dict:
        """Serialise the bountyDB and all of its bbBounties into dictionary format.

        :return: A dictionary containing all data needed to recreate this bountyDB.
        :rtype: dict
        """
        data = {"active": {}, "escaped": {}, "activity": self.activityMonitor.toDict()}
        # Serialise all factions into name : list of serialised bounty
        for fac in self.bounties:
            # Serialise all of the current faction's bounties into dictionary
            data["active"][fac] = [currentBounty.toDict(**kwargs) for currentBounty in self.getFactionBounties(fac)]

        # Serialise all factions into name : list of serialised escaped bounty
        for fac in self.escapedBounties:
            # Serialise all of the current faction's bounties into dictionary
            data["escaped"][fac] = [currentBounty.toDict(**kwargs) for currentBounty in self.escapedBounties[fac].values()]

        return data


    @classmethod
    def fromDict(cls, bountyDBDict : dict, **kwargs) -> BountyDB:
        """Build a bountyDB object from a serialised dictionary format - the reverse of bountyDB.toDict.

        :param dict bountyDBDict: a dictionary representation of the bountyDB, to convert to an object
        :param bool dbReload: Whether or not this bountyDB is being created during the initial database loading
                                phase of bountybot. This is used to toggle name checking in bounty contruction.

        :return: The new bountyDB object
        :rtype: bountyDB
        """
        dbReload = kwargs["dbReload"] if "dbReload" in kwargs else False
        if "owningBasedGuild" not in kwargs:
            raise ValueError("missing required kwarg: owningBasedGuild")

        escapedBountiesData = bountyDBDict["escaped"] if "escaped" in bountyDBDict \
                                else {fac: AliasableDict() for fac in bbData.factions}
        activeBountiesData = bountyDBDict["active"] if "active" in bountyDBDict \
                                else {fac: AliasableDict() for fac in bbData.factions}

        activity = guildActivity.ActivityMonitor.fromDict(bountyDBDict["activity"]) \
                    if "activity" in bountyDBDict else guildActivity.ActivityMonitor()

        # Instanciate a new bountyDB
        newDB = BountyDB(activeBountiesData.keys(), kwargs["owningBasedGuild"], activityMonitor=activity)
        # Iterate over all factions in the DB
        for fac in activeBountiesData.keys():
            # Convert each serialised bounty into a bounty object
            for bountyDict in activeBountiesData[fac]:
                newDB.addBounty(bounty.Bounty.fromDict(bountyDict, dbReload=dbReload, owningDB=newDB))
        # Iterate over all factions in the DB
        for fac in escapedBountiesData.keys():
            # Convert each serialised bounty into a bounty object
            for bountyDict in escapedBountiesData[fac]:
                newDB.addEscapedBounty(bounty.Bounty.fromDict(bountyDict, dbReload=dbReload, owningDB=newDB))
        return newDB
