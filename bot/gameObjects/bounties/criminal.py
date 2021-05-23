# Typing imports
from __future__ import annotations
from typing import List

from ...cfg import bbData
from ...baseClasses import aliasable
from ..items import shipItem


class Criminal(aliasable.Aliasable):
    """A criminal to be wanted in bounties.

    :var name: The name of the criminal
    :vartype name: str
    :var faction: the faction that this criminal is wanted by
    :vartype faction: str
    :var icon: A URL pointing to an image to use as the criminal's icon
    :vartype icon: str
    :var wiki: A URL pointing to a web page to use as this criminal's wiki page in their info embed
    :vartype wiki: str
    :var hasWiki: Whether or not this criminal has a wiki page
    :vartype hasWiki: bool
    :var isPlayer: Whether this criminal is a player or an NPC
    :vartype isPlayer: bool
    :var builtIn: If this criminal is an NPC, are they built in or custom?
    :vartype builtIn: bool
    """

    def __init__(self, name : str, faction : str, icon : str, builtIn : bool = False,
                    isPlayer : bool = False, aliases : List[str] = [], wiki : str = ""):
        """
        :param str name: The name of the criminal
        :param str faction: the faction that this criminal is wanted by
        :param str icon: A URL pointing to an image to use as the criminal's icon
        :param str wiki: A URL pointing to a web page to use as this criminal's wiki page in their info embed
        :param bool isPlayer: Whether this criminal is a player or an NPC
        :param bool builtIn: If this criminal is an NPC, are they built in or custom?
        :param list[str] aliases: Alias names that can be used to refer to this criminal
        """
        super(Criminal, self).__init__(name, aliases)
        if name == "":
            raise RuntimeError("CRIM_CONS_NONAM: Attempted to create a Criminal with an empty name")
        # if faction == "":
        #     raise RuntimeError("CRIM_CONS_NOFAC: Attempted to create a Criminal with an empty faction")
        if faction == "":
            raise RuntimeError("CRIM_CONS_NOICO: Attempted to create a Criminal with an empty icon")

        self.name = name
        self.faction = faction
        self.icon = icon
        self.wiki = wiki
        self.hasWiki = wiki != ""
        self.isPlayer = isPlayer
        self.builtIn = builtIn


    def toDict(self, **kwargs) -> dict:
        """Serialize this criminal into dictionary format, for saving to file.

        :return: A dictionary containing all data necessary to replicate this object
        :rtype: dict
        """
        if self.builtIn:
            return {"builtIn":True, "name":self.name}
        else:
            return {"builtIn": False, "isPlayer": self.isPlayer, "name": self.name, "icon": self.icon,
                    "faction": self.faction, "aliases": self.aliases, "wiki": self.wiki}


    @classmethod
    def fromDict(cls, crimDict : dict, **kwargs) -> Criminal:
        """Factory function that will either provide a reference to a builtIn criminal if a builtIn criminal is requested,
        or construct a new criminal object from the provided data.

        :param dict crimDict: A dictionary containing all data necessary to construct the desired criminal.
                                If the criminal is builtIn, this need only be their name, "builtIn": True,
                                and possibly the equipped ship.
        :return: The requested criminal object reference
        :rtype: criminal
        """
        builtIn = (kwargs["builtIn"] if "builtIn" in kwargs else False) or \
                    (crimDict["builtIn"] if "builtIn" in crimDict else False)

        if builtIn:
            return bbData.builtInCriminalObjs[crimDict["name"]]
        else:
            return Criminal(crimDict["name"], crimDict["faction"], crimDict["icon"], isPlayer=crimDict["isPlayer"],
                            aliases=crimDict["aliases"], wiki=crimDict["wiki"], builtIn=builtIn)
