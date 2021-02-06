from __future__ import annotations
from . import moduleItem
from ....cfg import bbData
from .... import lib
from typing import List
from ..gameItem import spawnableItem


@spawnableItem
class ArmourModule(moduleItem.ModuleItem):
    """A module providing a ship with an extra layer of defense.
    """
    def __init__(self, name : str, aliases : List[str], armour : int = 0, value : int = 0,
            wiki : str = "", manufacturer : str = "", icon : str = "",
            emoji : lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel : int = -1,
            builtIn : bool = False):
        """
        :param str name: The name of the module. Must be unique.
        :param list[str] aliases: Alternative names by which this module may be referred to
        :param int armour: The amount of armour this module adds to a ship (Default 0)
        :param int value: The number of credits this module may be sold or bought or at a shop (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this module. (Default "")
        :param str manufacturer: The name of the manufacturer of this module (Default "")
        :param str icon: A URL pointing to an image to use for this module's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for the module's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used
                                as a measure for its effectiveness compared to other modules of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard module (loaded in from bbData) or a
                                custom spawned module (Default False)
        """
        super(ArmourModule, self).__init__(name, aliases, armour=armour, value=value, wiki=wiki, manufacturer=manufacturer,
                                            icon=icon, emoji=emoji, techLevel=techLevel, builtIn=builtIn)

    
    def toDict(self, **kwargs) -> dict:
        """Serialize this module into dictionary format, to be saved to file.
        No extra attributes implemented by this class, so just eses the base moduleItem toDict method.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        itemDict = super(ArmourModule, self).toDict(**kwargs)
        return itemDict


    @classmethod
    def fromDict(cls, moduleDict : dict, **kwargs) -> ArmourModule:
        """Factory function building a new module object from the information in the provided dictionary.
        The opposite of this class's toDict function.

        :param moduleDict: A dictionary containing all information needed to construct the requested module
        :return: The new module object as described in moduleDict
        :rtype: dict
        """
        if "builtIn" in moduleDict and moduleDict["builtIn"]:
            return bbData.builtInModuleObjs[moduleDict["name"]]
            
        return ArmourModule(moduleDict["name"], moduleDict["aliases"] if "aliases" in moduleDict else [],
                                armour=moduleDict["armour"] if "armour" in moduleDict else 0,
                                value=moduleDict["value"] if "value" in moduleDict else 0,
                                wiki=moduleDict["wiki"] if "wiki" in moduleDict else "",
                                manufacturer=moduleDict["manufacturer"] if "manufacturer" in moduleDict else "",
                                icon=moduleDict["icon"] if "icon" in moduleDict else bbData.rocketIcon,
                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) if "emoji" in moduleDict else \
                                        lib.emojis.BasedEmoji.EMPTY,
                                techLevel=moduleDict["techLevel"] if "techLevel" in moduleDict else -1,
                                builtIn=moduleDict["builtIn"] if "builtIn" in moduleDict else False)