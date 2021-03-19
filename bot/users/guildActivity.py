from __future__ import annotations

from ..baseClasses.serializable import Serializable
from ..cfg import cfg
from typing import List

_numTLs = cfg.maxTechLevel - cfg.minTechLevel + 2
_tlsRange = range(_numTLs)

class ActivityMonitor(Serializable):
    """A measure of the level of player activity in a guild for each tech level.
    minTechLevel - 1 is included in this to record activity for level 0 bounties.

    Activity measures are stored as 'temperatures' - values that rise linearly with activity, but slowly decay with time.
    These operations are not automatic. raiseTemp should be called upon guild activity (currently when bounties are caught),
    and decayTemps should be called daily.

    :var temperatures: A list of floats representing the current level of player activity for bounties of a single
                        tech level in a single guild. Temperatures are stored at indices corresponding to tech levels, i.e
                        the temperature for level 4 bounties is stored at temperatures[4]
    :vartype temperatures: List[float]
    :var isActive: True if at least one temperature is higher than the minimum, False otherwise
    :vartype isActive: bool
    """

    def __init__(self, temps: List[float] = [cfg.minGuildActivity] * _numTLs):
        """
        :param List[float] temperatures: A list of floats representing the current level of player activity for bounties of a
                            single tech level in a single guild. Temperatures are stored at indices corresponding to tech
                            levels, i.e the temperature for level 4 bounties is stored at temps[4]
        """
        if len(temps) != _numTLs:
            raise ValueError("Temps must have exactly " + str(_numTLs) + " elements. Given " + len(temps) + " elements.")
        self.temperatures = [max(temps[tl], cfg.minGuildActivity) for tl in _tlsRange]
        self.isActive = False
        self.updateIsActive()


    def updateIsActive(self):
        """Manually updates the state of self.isActive by attempting to find a temperature above the minimum
        """
        self.isActive = bool(next((a for a in self.temperatures if a != cfg.minGuildActivity), None))


    def decayTemps(self, updateActive : bool = True):
        """Multiplies all temperatures by cfg.guildActivityDecayRate, with a lower temperature bount of cfg.minGuildActivity.

        :param bool updateActive: When True, self.updateIsActive will be called once temp decaying is complete (default True)
        """
        if self.isActive:
            for tl in _tlsRange:
                newTemp = self.temperatures[tl] * cfg.guildActivityDecayRate
                # truncate to 2 decimal places and lower bound
                self.temperatures[tl] = max(cfg.minGuildActivity, round(newTemp, 1))
            if updateActive:
                self.updateIsActive()


    def raiseTemp(self, tl: int, amount: float):
        """Raise a single temperature by a given amount. The operation is a simple addition.
        This operation always sets self.isActive to True.

        :param int tl: The techlevel corresponding with the temperature to raise
        :param float amount: The amount to raise the temperature by
        """
        self.temperatures[tl] += amount
        if not self.isActive:
            self.isActive = True


    def tlIsActive(self, tl: int) -> bool:
        """Decide whether or not players are active at a single tech level

        :param int tl: The techlevel to check for activity at
        :return: True if the temperature at the given techlevel is above the minimum, False otherwise
        :rtype: bool
        """
        return self.temperatures[tl] > cfg.minGuildActivity


    def measureTL(self, tl: int) -> float:
        """Read the current temperature for a one-indexed tech level.
        Using one-indexing allows for reading of tech level 0's temperature.

        :param int tl: The tech level to read
        :return: The currentl activity level at tech level tl
        :rtype: float
        """
        return self.temperatures[tl]


    def toDict(self, **kwargs) -> dict:
        """Serialize this ActivityMonitor into dictionary format, to be recreated completely.

        :return: A dictionary containing all of the current temperatures
        :rtype: dict
        """
        return {"temps": self.temperatures}


    @classmethod
    def fromDict(self, data: dict, **kwargs) -> ActivityMonitor:
        """Recreate a dictionary-serialized ActivityMonitor

        :param dict data: A dictionary containing all of the current temperatures
        :return: A ActivityMonitor object as specified by the attributes in data
        :rtype: ActivityMonitor
        """
        if "temps" in data:
            return ActivityMonitor(temps=data["temps"])
        else:
            return ActivityMonitor()
