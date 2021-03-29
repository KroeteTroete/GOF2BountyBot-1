from ..baseClasses.serializable import Serializable
from ..baseClasses.aliasableDict import AliasableDict
from ..gameObjects.bounties import criminal, bounty
from ..cfg import cfg, bbData

from typing import Dict


class BountyDivision(Serializable):
    def __init__(self, owningDB, minLevel: int, maxLevel: int) -> None:
        """
        :param BountyDB owningDB: The BountyDB that owns this division
        """
        # Dictionary of faction name : dict of criminal : bounty
        self.bounties: Dict[str, AliasableDict[criminal.Criminal, bounty.Bounty]] = {f: AliasableDict() \
                                                                                        for f in bbData.bountyFactions}
        # Dictionary of faction name : dict of criminal : bounty
        self.escapedBounties: Dict[str, AliasableDict[criminal.Criminal, bounty.Bounty]] = {f: AliasableDict() \
                                                                                                for f in bbData.bountyFactions}
        self.owningDB = owningDB
        self.levels = range(minLevel, maxLevel + 1)
        

    
