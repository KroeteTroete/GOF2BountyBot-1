import random
from typing import List
from . import toolItem
from .... import lib, botState
from discord import Message
from ....cfg import cfg
from .. import gameItem
from ....reactionMenus.confirmationReactionMenu import InlineConfirmationMenu
from ....users.basedUser import BasedUser


@gameItem.spawnableItem
class CrateTool(toolItem.ToolItem):
    """A tool containing a pool of GameItems which, when used, gives the user a single random item from the pool.
    Also automatically removes itself from the user's inventory upon use.

    :var itemPool: List of potential items to win. May contain duplicates.
    :vartype itemPool: List[gameItem.GameItem]
    """
    def __init__(self, itemPool: List[gameItem.GameItem], name : str = "", value : int = 0, wiki : str = "",
            manufacturer : str = "", icon : str = "", emoji : lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY,
            techLevel : int = -1, builtIn : bool = False):
        """
        :param List[gameItem.GameItem] itemPool: List of potential items to win. May contain duplicates.
        :param str name: The name of the crate. Must be unique.
        :param int value: The number of credits that this item can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this item. (Default "")
        :param str manufacturer: The name of the manufacturer of this item (Default "")
        :param str icon: A URL pointing to an image to use for this item's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for this item's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement, generally for crates this isn't
                                limited, e.g a measure of the rarity of the items, or of the items' TLs maybe (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard crate (loaded in from JSON) or a custom spawned
                                item (Default False)
        """

        super().__init__(name, [], value=value, wiki=wiki,
            manufacturer=manufacturer, icon=icon, emoji=emoji,
            techLevel=techLevel, builtIn=builtIn)

        try:
            item = next(i for i in itemPool if not gameItem.isSpawnableItemInstance(i))
        except StopIteration:
            self.itemPool = itemPool
        else:
            raise RuntimeError("Attempted to create a crateTool with something other than a spawnableItem " \
                                + "in its itemPool: " + str(item))


    async def use(self, *args, **kwargs):
        """Behaviour function which adds a random item from the pool and adds it to the owner's inventory,
        then removes the crate from their inventory. For use in a command, use userFriendlyUse

        :param BasedUser callingBUser: The user who owns the crate
        """
        if "callingBUser" not in kwargs:
            raise NameError("Required kwarg not given: callingBUser")
        if not isinstance(kwargs["callingBUser"], BasedUser):
            raise TypeError("Required kwarg is of the wrong type. Expected BasedUser or None, received " \
                            + type(kwargs["callingBUser"]).__name__)

        callingBUser = kwargs["callingBUser"]
        newItem = random.choice(self.itemPool)
        callingBUser.getInventoryForItem(newItem).addItem(newItem)
        callingBUser.inactiveTools.removeItem(self)


    async def userFriendlyUse(self, message : Message, *args, **kwargs) -> str:
        """A version of self.use intended to be called by users, where exceptions are never thrown in the case of
        user error, and results strings are always returned.

        :param Message message: The discord message that triggered this tool use
        :return: A user-friendly messge summarising the result of the tool use.
        :rtype: str
        """
        if "callingBUser" not in kwargs:
            raise NameError("Required kwarg not given: callingBUser")
        if kwargs["callingBUser"] is not None and type(kwargs["callingBUser"]).__name__ != "BasedUser":
            raise TypeError("Required kwarg is of the wrong type. Expected BasedUser or None, received " \
                            + type(kwargs["callingBUser"]).__name__)

        callingBUser = kwargs["callingBUser"]
        confirmMsg = await message.channel.send("Are you sure you want to open this crate?")
        confirmation = await InlineConfirmationMenu(confirmMsg, message.author,
                                                    cfg.toolUseConfirmTimeoutSeconds).doMenu()

        if cfg.defaultEmojis.reject in confirmation:
            return "🛑 Crate open cancelled."
        elif cfg.defaultEmojis.accept in confirmation:
            newItem = random.choice(self.itemPool)
            callingBUser.getInventoryForItem(newItem).addItem(newItem)
            callingBUser.inactiveTools.removeItem(self)

            return "🎉 Success! You got a " + newItem.name + "!"


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        if len(self.itemPool) > 9:
            return "*" + str(len(self.itemPool)) + " possible items*"
        else:
            return "*" + " • ".join(i.name for i in self.itemPool) + "*"


    def toDict(self, **kwargs) -> dict:
        """Serialize this tool into dictionary format.
        This step of implementation adds a 'type' string indicating the name of this tool's subclass.

        :return: The default gameItem toDict implementation, with an added 'type' field
        :rtype: dict
        """
        data = super().toDict(**kwargs)
        if "saveType" not in kwargs:
            kwargs["saveType"] = True

        data["itemPool"] = []
        for item in self.itemPool:
            data["itemPool"].append(item.toDict(**kwargs))
        return data


    @classmethod
    def fromDict(cls, crateDict, **kwargs):
        skipInvalidItems = kwargs.get("skipInvalidItems", False)

        itemPool = []
        if "itemPool" in crateDict:
            for itemDict in crateDict["itemPool"]:
                errorStr = ""
                errorType = ""
                if "type" not in itemDict:
                    errorStr = "Invalid itemPool entry, missing type. Data: " + itemDict
                    errorType = "NO_TYPE"
                elif itemDict["type"] not in gameItem.subClassNames:
                    errorStr = "Invalid itemPool entry, attempted to add something other than a spawnableItem. Data: " \
                                + str(itemDict)
                    errorType = "BAD_TYPE"
                if errorStr:
                    if skipInvalidItems:
                        botState.logger.log("crateTool", "fromDict", errorStr, eventType=errorType)
                    else:
                        raise ValueError(errorStr)
                else:
                    itemPool.append(gameItem.spawnItem(itemDict))
        else:
            botState.logger.log("crateTool", "fromDict", "fromDict-ing a crateTool with no itemPool.")

        return CrateTool(**cls._makeDefaults(crateDict, ("type",), itemPool=itemPool,
                                            emoji=lib.emojis.BasedEmoji.fromDict(crateDict["emoji"]) \
                                                    if "emoji" in crateDict else lib.emojis.BasedEmoji.EMPTY))
