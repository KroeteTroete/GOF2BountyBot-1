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

import random


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
    :var levelsRange: A range from minLevel to maxLevel, inclusive (i.e levelsRange.stop = maxLevel + 1)
    :vartype levelsRange: range
    :var bounties: A record of all currently active bounties, with tech levels as keys
    :vartype bounties: Dict[int, AliasableDict[Criminal, Bounty]]
    :var isActive: True if there is any player activity in this division currently, False otherwise
    :vartype isActive: bool
    """

    def __init__(self, owningDB: "BountyDB", minLevel: int, maxLevel: int) -> None:
        """
        :param BountyDB owningDB: The BountyDB that owns this division
        :param int minLevel: The lowest level of bounties available in this division
        :param int maxLevel: The highest level of bounties available in this division
        """
        self.temperature = 0.
        self.isActive = False
        self.updateIsActive()
        self.minLevel = minLevel
        self.maxLevel = maxLevel
        self.levelsRange = range(minLevel, maxLevel + 1)
        # Dictionary of tech level : dict of criminal : bounty
        self.bounties: Dict[int, AliasableDict[Criminal, Bounty]] = {l: AliasableDict() for l in self.levelsRange}
        # Dictionary of tech level : dict of criminal : bounty
        self.escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]] = {l: AliasableDict() for l in self.levelsRange}
        self.owningDB = owningDB


    def updateIsActive(self):
        """Manually updates the state of self.isActive by attempting to find a temperature above the minimum
        """
        self.isActive = bool(next((a for a in self.temperatures if a != cfg.minGuildActivity), None))


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
                return sum(len(self.bounties[l]) + len(self.escapedBounties[l]) for l in self.levelsRange)
            return sum(len(self.bounties[l]) for l in self.levelsRange)
        if includeEscaped:
            return len(self.bounties[level]) + len(self.escapedBounties[level])
        return len(self.bounties[level])


    def maxBounties(self) -> int:
        """Decide the maximum number of bounties that the division can currently contain, based on the level of
        player activity.

        :return: The maximum number of bounties the division can currently contain
        :rtype: int
        """
        return cfg.maxBountiesPerDivision if self.isActive else 1
        

    async def spawnNewBounty(self) -> Bounty:
        """Generate, spawn and announce a random bounty.
        This method ensures that at least one bounty is present at the min tech level of the division,
        and will spawn bounties at random levels otherwise.

        :return: The newly spawned bounty object
        :rtype: Bounty
        :raise OverflowError: If the division is currently full
        """
        if self.getNumBounties(includeEscaped=True) >= self.maxBounties():
            raise OverflowError("Attempted to spawn a new bounty when the DB is currently full")

        if len(self.bounties[self.minLevel]) == 0:
            level = self.minLevel
        else:
            level = random.choice(self.levelsRange)

        newBounty = Bounty(config=BountyConfig(techLevel=level).generate(owningDB=self.owningDB))
        self.bounties[level][newBounty.criminal] = newBounty

        await self.owningDB.owningBasedGuild.announceNewBounty(newBounty)


    async def respawnBounty(self, bounty: Bounty):
        """Regenerate, respawn and announce the given escaped bounty.
        The bounty's attributes are modified in place, no new Bounty object is created.

        :raise OverflowError: If the division is currently full
        :raise KeyError: When given a bounty that is not stored in this division's escaped bounties
        :raise IndexError: When given a bounty whose tech level is not stored in this division
        """
        if bounty.criminal not in self.bounties[bounty.techLevel]:
            raise KeyError("Attempted to respawn a bounty that is not registered as an escaped bounty: " \
                            + bounty.criminal.name)
        if self.getNumBounties(includeEscaped=False) >= self.maxBounties():
            raise OverflowError("Attempted to respawn a bounty when the DB is currently full: " + bounty.criminal.name)
        if bounty.techLevel not in self.levelsRange:
            raise IndexError("Attempted to respawn a bounty whose tech level is not stored in this division: " \
                                + bounty.criminal.name + " (" + str(bounty.techLevel) + ")")

        del self.escapedBounties[bounty.techLevel][bounty.criminal]
        bounty.__init__(config=bounty.makeRespawnConfig().generate(owningDB=self.owningDB))
        self.bounties[bounty.techLevel][bounty.criminal] = bounty

        await self.owningDB.owningBasedGuild.announceNewBounty(bounty)
