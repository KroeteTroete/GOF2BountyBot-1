from __future__ import annotations
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from .bountyDB import BountyDB

from ..baseClasses.serializable import Serializable
from ..baseClasses.aliasableDict import AliasableDict
from ..gameObjects.bounties.bounty import Bounty
from ..gameObjects.bounties.criminal import Criminal
from ..gameObjects.bounties.bountyConfig import BountyConfig
from ..cfg import cfg, bbData
from .. import botState, lib
from ..scheduling.timedTask import TimedTask, DynamicRescheduleTask

from datetime import timedelta
import random
from typing import List


class BountyDivision(Serializable):
    """A database of Bounties for a range of tech levels.
    The maximum capacity and spawning rates of bounties are based on the "temperature" of the division - an estimate for the
    level of player activity.

    :var temperature: A measure of the level of player activity in this division.
    :vartype temperature: float
    :var minLevel: The lowest level of bounties available in this division
    :varype minLevel: int
    :var maxLevel: The highest level of bounties available in this division
    :varype maxLevel: int
    :var bounties: A record of all currently active bounties, with tech levels as keys
    :vartype bounties: Dict[int, AliasableDict[Criminal, Bounty]]
    :var latestBounty: The most recent bounty to be added to this division. As of writing,
                        this is only used when scaling new bounty delays by the most recent length
    :vartype latestBounty: Union[Bounty, None]
    :var escapedBounties: A record of all currently escaped, inactive bounties, with tech levels as keys
    :vartype escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]]
    :var isActive: True if there is any player activity in this division currently, False otherwise
    :vartype isActive: bool
    :var delayRandRange: A dictionary containing boundary timedeltas for use in random bounty delay generators
    :vartype delayRandRange: Dict[str, timedelta]
    """
    delayRandRange = {"min": timedelta(**cfg.timeouts.newBountyDelayRandomMin),
                        "max": timedelta(**cfg.timeouts.newBountyDelayRandomMax)}

    def __init__(self, owningDB: "BountyDB", minLevel: int, maxLevel: int, temperature: int = cfg.minGuildActivity,
                bounties: Dict[int, AliasableDict[Criminal, Bounty]] = None,
                escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]] = None) -> None:
        """
        :param BountyDB owningDB: The BountyDB that owns this division
        :param int minLevel: The lowest level of bounties available in this division
        :param int maxLevel: The highest level of bounties available in this division
        """
        self.temperature = temperature
        self.isActive = False
        self.updateIsActive()
        self.minLevel = minLevel
        self.maxLevel = maxLevel
        self.latestBounty: Bounty = None
        # Dictionary of tech level : dict of criminal : bounty
        if bounties is None:
            self.bounties: Dict[int, AliasableDict[Criminal, Bounty]] = {l: AliasableDict()
                                                                        for l in range(self.minLevel, self.maxLevel + 1)}
        else:
            self.bounties = bounties
            for tlBounties in self.bounties.values():
                for bty in tlBounties.values():
                    if self.latestBounty is None or bty.issueTime > self.latestBounty.issueTime:
                        self.latestBounty = bty

        # Dictionary of tech level : dict of criminal : bounty
        if escapedBounties is None:
            self.escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]] = {l: AliasableDict()
                                                                        for l in range(self.minLevel, self.maxLevel + 1)}
        else:
            self.escapedBounties = escapedBounties
        self.owningDB = owningDB

        bountyDelayGenerators = {"random": lib.timeUtil.getRandomDelay,
                                "fixed-routeScale": self.getRouteScaledBountyDelayFixed,
                                "random-routeScale": self.getRouteScaledBountyDelayRandom,
                                "random-routeScale-tempScale": self.getRouteTempScaledBountyDelayRandom}

        bountyDelayGeneratorArgs = {"random": self.delayRandRange,
                                    "fixed-routeScale": cfg.newBountyFixedDelta,
                                    "random-routeScale": self.delayRandRange,
                                    "random-routeScale-tempScale": self.delayRandRange}

        # linear temperature-maxBounty scaling
        self.maxBounties: min(int(self.temperature), cfg.maxBountiesPerDivision)

        if cfg.newBountyDelayType == "fixed":
            self.newBountyTT = TimedTask(expiryDelta=timedelta(**cfg.newBountyFixedDelta),
                                        expiryFunction=self.spawnNewBounty, autoReschedule=True,
                                        rescheduleOnExpiryFuncFailure=True)
        else:
            self.newBountyTT = DynamicRescheduleTask(bountyDelayGenerators[cfg.newBountyDelayType], autoReschedule=True,
                                                    delayTimeGeneratorArgs=bountyDelayGeneratorArgs[cfg.newBountyDelayType],
                                                    rescheduleOnExpiryFuncFailure=True, expiryFunction=self.spawnNewBounty)

        botState.taskScheduler.scheduleTask(self.newBountyTT)


    def updateIsActive(self):
        """Manually updates the state of self.isActive by attempting to find a temperature above the minimum
        """
        self.isActive = self.temperature != cfg.minGuildActivity


    def getNumBounties(self, level : int = -1, includeEscaped : bool = True) -> int:
        """Decide the number of bounties currently stored in this division.
        Give a tech level for the number of bounties at that level, or -1 for a count across all levels.
        If includeEscaped is given as true, escaped bounties will also be counted.

        :param int level: The tech level whose bounties to count, or -1 for all levels (Default -1)
        :param bool includeEscaped: Whether or not to count escaped bounties as well as active bounties (Default True)
        :return: The number of bounties stored at the given level if one is provided, or in the entire division if given -1
        :rtype: int
        """
        if level == -1:
            if includeEscaped:
                return sum(len(self.bounties[l]) + len(self.escapedBounties[l])
                            for l in range(self.minLevel, self.maxLevel + 1))
            return sum(len(self.bounties[l]) for l in range(self.minLevel, self.maxLevel + 1))
        if includeEscaped:
            return len(self.bounties[level]) + len(self.escapedBounties[level])
        return len(self.bounties[level])


    def bountyObjExists(self, bounty : Bounty) -> bool:
        """Check whether a given bounty object exists in the division.
        Existence is checked by checking if the bounty's criminal is in the division at the bounty's level.

        :param Bounty bounty: The bounty object to check for existence in the division
        :return: True if the bounty's criminal exists here at the bounty's level
        :rtype: bool
        """
        return bounty.criminal in self.bounties[bounty.techLevel]


    def criminalObjExists(self, crim : Criminal) -> bool:
        """Check whether a given criminal object exists in the division.
        Existence is checked across all levels.

        :param Criminal crim: The criminal object to check for existence in the division
        :return: True if the given criminal is found at any level in the division, False otherwise
        :rtype: bool
        """
        return any((crim in tlBounties) for tlBounties in self.bounties.keys())


    def escapedCriminalExists(self, crim):
        """Decide whether a criminal is recorded in the escaped criminals database.
        
        :param criminal crim: The criminal to check for existence
        :return: True if crim is in this division's escaped criminals record, False otherwise
        :rtype: bool
        """
        return any((crim in tlBounties) for tlBounties in self.escapedBounties.keys())


    def maxBounties(self) -> int:
        """Decide the maximum number of bounties that the division can currently contain, based on the level of
        player activity.

        :return: The maximum number of bounties the division can currently contain
        :rtype: int
        """
        return cfg.maxBountiesPerDivision if self.isActive else 1


    def pickNewTL(self) -> int:
        """Pick a tech level for a new bounty.
        In ascending order, if a tech level has no bounties, it is returned.
        If all tech levels have at least one bounty, a level is picked at random.

        :return: A tech level to be spawned into this division
        :rtype: int
        :raise OverflowError: When the division has no more space for bounties
        """
        if self.isFull():
            raise OverflowError("Attempted to spawn a new bounty when the DB is currently full")
        try:
            return next(l for l in range(self.minLevel, self.maxLevel + 1) if not self.bounties[l])
        except StopIteration:
            return random.randint(self.minLevel, self.maxLevel)
        

    async def spawnNewBounty(self) -> Bounty:
        """Generate, spawn and announce a random bounty.
        This method ensures that at least one bounty is present at the min tech level of the division,
        and will spawn bounties at random levels otherwise.

        :return: The newly spawned bounty object
        :rtype: Bounty
        :raise OverflowError: If the division is currently full
        """
        level = self.pickNewTL()

        newBounty = Bounty(division=self, config=BountyConfig(techLevel=level).generate(self))
        self.bounties[level][newBounty.criminal] = newBounty

        await self.owningDB.owningBasedGuild.announceNewBounty(newBounty)


    async def respawnBounty(self, bounty: Bounty):
        """Regenerate, respawn and announce the given escaped bounty.
        The bounty's attributes are modified in place, no new Bounty object is created.

        :raise OverflowError: If the division is currently full
        :raise KeyError: When given a bounty that is not stored in this division's escaped bounties
        :raise IndexError: When given a bounty whose tech level is not stored in this division
        """
        if bounty.criminal not in self.escapedBounties[bounty.techLevel]:
            raise KeyError("Attempted to respawn a bounty that is not registered as an escaped bounty: " \
                            + bounty.criminal.name)
        if self.getNumBounties(includeEscaped=False) >= self.maxBounties():
            raise OverflowError("Attempted to respawn a bounty when the DB is currently full: " + bounty.criminal.name)
        if bounty.techLevel < self.minLevel or bounty.techLevel > self.maxLevel:
            raise IndexError("Attempted to respawn a bounty whose tech level is not stored in this division: " \
                                + bounty.criminal.name + " (" + str(bounty.techLevel) + ")")

        del self.escapedBounties[bounty.techLevel][bounty.criminal]
        bounty.__init__(config=bounty.makeRespawnConfig().generate(self))
        self.bounties[bounty.techLevel][bounty.criminal] = bounty

        await self.owningDB.owningBasedGuild.announceNewBounty(bounty)


    def decayTemp(self, updateActive : bool = True):
        """Multiplies the activity temperature by cfg.guildActivityDecayRate,
        with a lower temperature bound of cfg.minGuildActivity.

        :param bool updateActive: When True, self.updateIsActive will be called once temp decaying is complete (default True)
        """
        if self.isActive:
            # truncate to 2 decimal places and lower bound
            self.temperature = max(cfg.minGuildActivity, round(self.temperature * cfg.guildActivityDecayRate, 1))
            if updateActive:
                self.updateIsActive()


    def raiseTemp(self, amount: float):
        """Raise the activity temperature by a given amount. The operation is a simple addition.
        This operation always sets self.isActive to True.

        :param float amount: The amount to raise the temperature by
        """
        self.temperature += amount
        if not self.isActive:
            self.isActive = True


    def getRouteScaledBountyDelayFixed(self, baseDelayDict: Dict[str, timedelta]) -> timedelta:
        """New bounty delay generator, scaling a fixed delay by the length of the presently spawned bounty.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if self.latestBounty is None else len(self.latestBounty.route)
        delay = timedelta(**baseDelayDict) * timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if self.latestBounty is None else \
                                (f"latest criminal: '{self.latestBounty.criminal.name}' Route {len(self.latestBounty.route)}")
            botState.logger.log("Main", "routeScaleBntyDelayFixed",
                                f"New bounty delay generated, {latestCriminal}" \
                                    + f"\nDelay picked: {lib.timeUtil.td_format_noYM(delay)}",
                                category="newBounties",
                                eventType="NONE_BTY" if self.latestBounty is None else "DELAY_GEN", noPrint=True)
        return delay


    def getRouteScaledBountyDelayRandom(self, baseDelayDict: Dict[str, timedelta]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if self.latestBounty is None else len(self.latestBounty.route)
        delay = lib.timeUtil.getRandomDelay({"min": baseDelayDict["min"], "max": baseDelayDict["max"]})
        delay *= timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if self.latestBounty is None else \
                                (f"latest criminal: '{self.latestBounty.criminal.name}' Route {len(self.latestBounty.route)}")
            minTime = (baseDelayDict["min"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            maxTime = (baseDelayDict["max"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            botState.logger.log("Main", "routeScaleBntyDelayRand",
                                f"New bounty delay generated, {latestCriminal}" \
                                    + f"\nRange: " \
                                        + f"{lib.timeUtil.td_format_noYM(minTime)} - {lib.timeUtil.td_format_noYM(maxTime)}" \
                                    + f"\nDelay picked: {lib.timeUtil.td_format_noYM(delay)}",
                                category="newBounties",
                                eventType="NONE_BTY" if self.latestBounty is None else "DELAY_GEN", noPrint=True)

        return delay


    def getRouteTempScaledBountyDelayRandom(self, baseDelayDict: Dict[str, timedelta]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty and the current activity temperature at the
        presently spawned bounty's tech level.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if self.latestBounty is None else len(self.latestBounty.route)
        tempScale = self.temperature ** - 0.1
        delay = lib.timeUtil.getRandomDelay({"min": baseDelayDict["min"], "max": baseDelayDict["max"]})
        delay *= tempScale * timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if self.latestBounty is None else \
                                (f"latest criminal: '{self.latestBounty.criminal.name}' Route {len(self.latestBounty.route)}")
            minTime = (baseDelayDict["min"] * timeScale * tempScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            maxTime = (baseDelayDict["max"] * timeScale * tempScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            botState.logger.log("Main", "getRouteTempScaledBountyDelayRandom",
                                f"New bounty delay generated, temp {self.temperature} -> scale {tempScale:.2f}" \
                                    + f"\n{latestCriminal}"
                                    + f"\nRange: " \
                                        + f"{lib.timeUtil.td_format_noYM(minTime)} - {lib.timeUtil.td_format_noYM(maxTime)}" \
                                    + f"\nDelay picked: {lib.timeUtil.td_format_noYM(delay)}",
                                category="newBounties",
                                eventType="NONE_BTY" if self.latestBounty is None else "DELAY_GEN", noPrint=True)
        return delay


    def isEmpty(self, includeEscaped: bool = True) -> bool:
        """Decide whether this division contains any bounties.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if there are no bounties in the division, False otherwise
        :rtype: bool
        """
        if includeEscaped:
            return any(self.bounties.values()) or any(self.escapedBounties.values())
        else:
            return any(self.bounties.values())


    def isFull(self, includeEscaped: bool = True) -> bool:
        """Decide whether this division has space for more bounties.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if the division is at capacity, False otherwise
        :rtype: bool
        """
        return self.getNumBounties(includeEscaped=includeEscaped) >= cfg.maxBountiesPerDivision


    async def clear(self, includeEscaped: bool = True):
        """Remove all bounties from the division.

        :param bool includeEscaped: Whether to also clear escaped bounties (Default True)
        """
        for tlBounties in self.bounties.values():
            tlBounties.clear()
        if includeEscaped:
            for tlBounties in self.escapedBounties.values():
                for bty in tlBounties:
                    await bty.respawnTT.forceExpire(callExpiryFunc=False)
                tlBounties.clear()


    async def resetNewBountyCool(self):
        """Force expiry on the new bounty TimedTask, immediately triggering a new bounty spawn.
        """
        await self.newBountyTT.forceExpire(callExpiryFunc=True)


    def toDict(self, **kwargs) -> dict:
        """Serialize this division into dictionary format, to be recreated completely.

        :return: A dictionary containing all of the current bounties and the activity temperature
        :rtype: dict
        """
        return {"temperature": self.temperature, "minLevel": self.minLevel, "maxLevel": self.maxLevel,
                "bounties": {l: [b.toDict(**kwargs) for b in self.bounties[l]]
                            for l in range(self.minLevel, self.maxLevel + 1) if self.bounties[l]},
                "escapedBounties": {l: [b.toDict(**kwargs) for b in self.escapedBounties[l]]
                            for l in range(self.minLevel, self.maxLevel + 1) if self.escapedBounties[l]}}


    @classmethod
    def fromDict(cls, data: dict, owningDB : "BountyDB" = None, **kwargs) -> BountyDivision:
        """Recreate a dictionary-serialized BountyDivision

        :param dict data: A dictionary containing all of the current bounties and the current activity temperature
        :return: A BountyDivision object as specified by the attributes in data
        :rtype: BountyDivision
        """
        if type(owningDB) != BountyDB:
            raise ValueError(f"Expected type BountyDB for kwarg owningDB but received {type(owningDB.__name__)}")
        crims = set()

        bounties = {l: AliasableDict() for l in range(data["minLevel"], data["maxLevel"] + 1)}
        if "bounties" in data:
            for l in data["bounties"]:
                for bty in data["bounties"][l]:
                    newBounty = Bounty.fromDict(bty, owningDB=owningDB, **kwargs)
                    if newBounty.criminal in crims:
                        botState.logger.log("BountyDivision", "fromDict",
                                            f"2 listings for the same criminal found: {bty.criminal.name}. Ignoring one." \
                                                + "Neither was escaped.", category="bountiesDB", eventType="DUPE_CRIM")
                    else:
                        crims.add(newBounty.criminal)
                        bounties[l][newBounty.criminal] = newBounty

        escapedBounties = {l: AliasableDict() for l in range(data["minLevel"], data["maxLevel"] + 1)}
        if "escapedBounties" in data:
            for l in data["escapedBounties"]:
                for bty in data["escapedBounties"][l]:
                    newBounty = Bounty.fromDict(bty, owningDB=owningDB, **kwargs)
                    if newBounty.criminal in crims:
                        botState.logger.log("BountyDivision", "fromDict",
                                            f"2 listings for the same criminal found: {bty.criminal.name}. Ignoring one." \
                                                + "At least one was escaped.", category="bountiesDB", eventType="DUPE_CRIM")
                    else:
                        crims.add(newBounty.criminal)
                        escapedBounties[l][newBounty.criminal] = newBounty

        return BountyDivision(owningDB, data["minLevel"], data["maxLevel"],
                                **cls._makeDefaults(data, bounties=bounties, escapedBounties=escapedBounties))
