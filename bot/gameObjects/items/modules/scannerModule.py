from . import moduleItem
from ....cfg import bbData
from .... import lib
from typing import List
from ..gameItem import spawnableItem


@spawnableItem
class ScannerModule(moduleItem.ModuleItem):
    """A module providing a ship with the ability to scan in-range objects, such as asteroids and ships

    :var timeToLock: The number of seconds this scanner takes to lock onto an object and obtain information
    :vartype timeToLock: float
    :var showClassAAsteroids: Whether or not this scanner will display nearby A-class asteroids on the ship's heads up display
    :vartype showClassAAsteroids: bool
    :var showCargo: Whether or not this scanner will display the contents of scanned ships' cargo holds
    :vartype showCargo: bool
    """

    def __init__(self, name : str, aliases : List[str], timeToLock : int = 0,
            showClassAAsteroids : bool = False, showCargo : bool = False, value : int = 0,
            wiki : str = "", manufacturer : str = "", icon : str = "",
            emoji : lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel : int = -1,
            builtIn : bool = False):
        """
        :param str name: The name of the module. Must be unique.
        :param list[str] aliases: Alternative names by which this module may be referred to
        :param float timeToLock: The number of seconds this scanner takes to lock onto an object and
                                    obtain information (Default 0)
        :param bool showClassAAsteroids: Whether or not this scanner will display nearby A-class asteroids
                                            on the ship's heads up display (Default False)
        :param bool showCargo: Whether or not this scanner will display the contents of scanned ships'
                                cargo holds (Default False)
        :param int value: The number of credits this module may be sold or bought or at a shop (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this module. (Default "")
        :param str manufacturer: The name of the manufacturer of this module (Default "")
        :param str icon: A URL pointing to an image to use for this module's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for the module's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used
                                as a measure for its effectiveness compared to other modules of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard module (loaded in from bbData) or
                                a custom spawned module (Default False)
        """
        super(ScannerModule, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                                            emoji=emoji, techLevel=techLevel, builtIn=builtIn)

        self.timeToLock = timeToLock
        self.showClassAAsteroids = showClassAAsteroids
        self.showCargo = showCargo


    def statsStringShort(self):
        return "*Time To Lock: " + str(self.timeToLock) \
                + "s, Show Class A Asteroids: " + ("Yes" if self.showClassAAsteroids else "No") \
                + ", Show Cargo: " + ("Yes" if self.showCargo else "No") + "*"


    def toDict(self, **kwargs) -> dict:
        """Serialize this module into dictionary format, to be saved to file. Uses the base moduleItem toDict
        method as a starting point, and adds extra attributes implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        itemDict = super(ScannerModule, self).toDict(**kwargs)
        if not self.builtIn:
            itemDict["timeToLock"] = self.timeToLock
            itemDict["showClassAAsteroids"] = self.showClassAAsteroids
            itemDict["showCargo"] = self.showCargo
        return itemDict


    @classmethod
    def fromDict(cls, moduleDict : dict, **kwargs):
        """Factory function building a new module object from the information in the provided dictionary.
        The opposite of this class's toDict function.

        :param moduleDict: A dictionary containing all information needed to construct the requested module
        :return: The new module object as described in moduleDict
        :rtype: dict
        """
        if moduleDict.get("builtIn", False):
            return bbData.builtInModuleObjs[moduleDict["name"]]

        return ScannerModule(**cls._makeDefaults(moduleDict, ignores=("type",),
                                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) \
                                                        if "emoji" in moduleDict else lib.emojis.BasedEmoji.EMPTY))
