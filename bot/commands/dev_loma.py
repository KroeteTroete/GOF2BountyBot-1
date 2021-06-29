import discord
import json

from . import commandsDB as botCommands
from .. import lib, botState
from ..lib.stringTyping import commaSplitNum
from ..cfg import cfg
from ..gameObjects.items import gameItem
from ..users.basedUser import BasedUser
from ..gameObjects.lomaShop import LomaShop
from ..gameObjects.inventories.inventoryListing import DiscountableItemListing
from ..gameObjects.itemDiscount import ItemDiscount


botCommands.addHelpSection(3, "loma")

async def dev_cmd_loma_give(message : discord.Message, args : str, isDM : bool):
    """developer command spawning the described item and item discount, and placing it in the given user's loma shop.
    user must be either a mention or an ID or empty (to give the item to the calling user).
    type must be in cfg.validItemNames (but not 'all')
    item must be a json format description in line with the item's to and fromDict functions.
    item discount must be a json format description in line with ItemDiscount.fromDict.

    :param discord.Message message: the discord message calling the command
    :param str args: string, containing either a user ID or mention or nothing (to give item to caller), followed by a string
                        from cfg.validItemNames (but not 'all'), followed by a serialized item, and a serialized ItemDiscount
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedUser: BasedUser = None
    argsSplit = args.split(" ")
    if not lib.stringTyping.isInt(argsSplit[0]) and not lib.stringTyping.isMention(argsSplit[0]):
        requestedUser = botState.usersDB.getOrAddID(message.author.id)
        itemStr = args

    # otherwise get the specified user's bb object
    # [!] no validation is done.
    else:
        requestedUser = botState.usersDB.getOrAddID(int(argsSplit[0].lstrip("<@!").rstrip(">")))
        itemStr = args[len(argsSplit[0]) + 1:]

    itemType = itemStr.split(" ")[0].lower()

    itemDict = json.loads(itemStr[len(itemStr.split(" ")[0]):])
    if itemDict[0] != "{":
        await message.channel.send("item dictionary must start with {")
        return
    
    bracesSeen = 1
    itemDictEnd = -1
    for charNum, char in enumerate(itemDict[1:]):
        if char == "{":
            bracesSeen += 1
        elif char == "}":
            bracesSeen -= 1
            if bracesSeen == 0:
                itemDictEnd = charNum + 2
    
    discountDict = itemDict[itemDictEnd:]
    itemDict = itemDict[:itemDictEnd]
    print("DISCOUNTDICT:",discountDict)
    print("ITEMDICT",itemDict)

    if "type" not in itemDict:
        await message.channel.send(":x: Please give a type in your item dictionary.")
        return

    if itemDict["type"] not in gameItem.subClassNames:
        await message.channel.send(":x: Unknown gameItem subclass type: " + itemDict["type"])
        return


    if itemType == "all" or itemType not in cfg.validItemNames:
        await message.channel.send(":x: Invalid item type arg - " + itemType)
        return

    newItem = gameItem.spawnItem(itemDict)

    if requestedUser.loma is None:
        requestedUser.loma = LomaShop()
    itemStock = requestedUser.loma.getStockByName(itemType)
    itemStock.addItem(newItem)
    itemListing: DiscountableItemListing = itemStock.getListing(newItem)
    itemListing.pushDiscount(ItemDiscount.fromDict(discountDict))

    await message.channel.send(":white_check_mark: Given one '" + newItem.name + "' to **" \
                                + lib.discordUtil.userOrMemberName(botState.client.get_user(requestedUser.id),
                                                                                            message.guild) + "**!")

botCommands.register("loma-give", dev_cmd_loma_give, 3, forceKeepArgsCasing=True, allowDM=True, helpSection="loma", useDoc=True)


async def dev_cmd_debug_loma(message : discord.Message, args : str, isDM : bool):
    """developer command printing the requested user's loma, including object memory addresses.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention or ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not (lib.stringTyping.isInt(args) or lib.stringTyping.isMention(args)):
        await message.author.send(":x: Invalid user!")
        return

    requestedUser = botState.client.get_user(int(args.lstrip("<@!").rstrip(">")))
    if requestedUser is None:
        await message.author.send(":x: Unrecognised user!")
        return

    if not botState.usersDB.idExists(requestedUser.id):
        await message.author.send("User has not played yet!")
        return

    requestedBBUser: BasedUser = botState.usersDB.getUser(requestedUser.id)
    if requestedBBUser.loma is None:
        await message.author.send(":x: The requested pilot has no loma!")
        return
    if requestedBBUser.loma.isEmpty():
        await message.author.send(":x: The loma is empty!")
        return





    shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Loma",
                                            desc=requestedUser.mention,
                                            footerTxt="All items",
                                            thumb=requestedUser.avatar_url_as(size=64))

    itemTypes = ("ship", "weapon", "module", "turret", "tool")
    for itemType in itemTypes:
        itemInv = requestedBBUser.loma.getStockByName(itemType)
        await message.author.send(itemType.upper() + " KEYS: " + str(itemInv.keys) + "\n" + itemType.upper() \
                                    + " LISTINGS: " + str(list(itemInv.items.keys())))

    for currentItemType in itemTypes:
        currentStock = requestedBBUser.loma.getStockByName(currentItemType)
        for itemNum in range(1, currentStock.numKeys + 1):
            if itemNum == 1:
                shopEmbed.add_field(name="‎", value="__**" + currentItemType.title() + "s**__", inline=False)

            try:
                currentItem = currentStock[itemNum - 1].item
            except KeyError:
                try:
                    botState.logger.log("dev_loma", "dev_cmd_debug_loma",
                                        "Requested " + currentItemType + " '" + currentStock.keys[itemNum-1].name \
                                            + "' (index " + str(itemNum-1) \
                                            + "), which was not found in the shop stock",
                                        category="shop", eventType="UNKWN_KEY")
                except IndexError:
                    break
                except AttributeError as e:
                    keysStr = ""
                    for item in currentStock.items:
                        keysStr += str(item) + ", "
                    botState.logger.log("dev_loma", "dev_cmd_debug_loma",
                                        "Unexpected type in " + currentItemType + "sStock KEYS, index " \
                                            + str(itemNum-1) + ". Got " \
                                            + type(currentStock.keys[itemNum-1]).__name__ + ".\nInventory keys: " \
                                            + keysStr[:-2],
                                        category="shop", eventType="INVTY_KEY_TYPE")
                    shopEmbed.add_field(name=str(itemNum) + ". **⚠ #INVALID-ITEM# '" \
                                            + currentStock.keys[itemNum-1] + "'",
                                        value="Do not attempt to buy. Could cause issues.", inline=True)
                    continue
                shopEmbed.add_field(name=str(itemNum) + ". **⚠ #INVALID-ITEM# '" \
                                        + currentStock.keys[itemNum-1].name + "'",
                                    value="Do not attempt to buy. Could cause issues.", inline=True)
                continue
            
            itemListing: DiscountableItemListing = currentStock.getListing(currentItem)
            currentItemCount = itemListing.count
            if itemListing.discounts:
                discountedValue = int(currentItem.value * itemListing.discounts[0])
                discountAmountStr = f"{itemListing.discounts[0]*100:.2f}".rstrip("0.")
                valueStr = f"~~{commaSplitNum(currentItem.value)}~~ {commaSplitNum(discountedValue)}" \
                            + f" Credits\n*{'+' if itemListing.discounts[0] > 1 else '-'}" \
                            + f"{discountAmountStr}% : {itemListing.discounts[0].desc}\n"
            else:
                valueStr = f"{commaSplitNum(discountedValue)} Credits\n"
            shopEmbed.add_field(name=str(itemNum) + ". " \
                                    + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                    + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                    + "**" + currentItem.name + "**",
                                value=valueStr + currentItem.statsStringShort(), inline=True)

    try:
        await message.author.send(embed=shopEmbed)
    except discord.Forbidden:
        await message.channel.send(":x: I can't DM you, " + message.author.display_name \
            + "! Please enable DMs from users who are not friends.")
        return
    await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)

botCommands.register("debug-loma", dev_cmd_debug_loma, 3, allowDM=True, helpSection="loma", useDoc=True)