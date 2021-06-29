import discord

from . import commandsDB as bbCommands
from .. import botState, lib
from ..lib.stringTyping import commaSplitNum
from ..lib import gameMaths
from ..cfg import cfg
from ..gameObjects import lomaShop
from ..users.basedUser import BasedUser
from ..gameObjects.inventories.inventoryListing import DiscountableItemListing


bbCommands.addHelpSection(0, "loma")


async def cmd_loma(message : discord.Message, args : str, isDM : bool):
    """list the items currently available in the user's loma shop.
    Can specify an item type to list. TODO: Make specified item listings more detailed as in !bb bounties

    :param discord.Message message: the discord message calling the command
    :param str args: either empty string, or one of bbConfig.validItemNames
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
    if args.startswith("buy"):
        await cmd_loma_buy(message, args[5:].lstrip(" "), isDM)
        return
    elif args.startswith("sell"):
        await message.channel.send(":x: The Loma pirates do not buy items, they only sell.\nFor private item storage," \
                                    f" consider `{commandPrefix}kaamo`. If you need money, then `{commandPrefix}sell` to " \
                                    f"a server's `{commandPrefix}shop`.")
        return

    item = "all"
    if args.rstrip("s") in cfg.validItemNames:
        item = args.rstrip("s")
    elif args != "":
        await message.channel.send(":x: Invalid item type! (ship/weapon/module/turret/tool/all)")
        return

    sendChannel = None
    sendDM = False
    callingBBUser: BasedUser = botState.usersDB.getOrAddID(message.author.id)

    if item == "all":
        if message.author.dm_channel is None:
            await message.author.create_dm()
        if message.author.dm_channel is None:
            await message.channel.send(":x: I can't DM you, " + message.author.display_name \
                                        + "! Please enable DMs from users who are not friends.")
            return
        else:
            sendChannel = message.author.dm_channel
            sendDM = True
    else:
        sendChannel = message.channel

    shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Loma",
                                            desc=message.author.mention,
                                            footerTxt="All items" if item == "all" else (item + "s").title(),
                                            thumb=message.author.avatar_url_as(size=64))

    if callingBBUser.loma is None or callingBBUser.loma.isEmpty():
        shopEmbed.add_field(name="‎", value="No items currently available.")
    else:
        for currentItemType in ["ship", "weapon", "module", "turret", "tool"]:
            if item in ["all", currentItemType]:
                currentStock = callingBBUser.loma.getStockByName(currentItemType)
                for itemNum in range(1, currentStock.numKeys + 1):
                    if itemNum == 1:
                        shopEmbed.add_field(name="‎", value="__**" + currentItemType.title() + "s**__", inline=False)

                    try:
                        currentItem = currentStock[itemNum - 1].item
                    except KeyError:
                        try:
                            botState.logger.log("Main", "cmd_loma",
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
                            botState.logger.log("Main", "cmd_loma",
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
        await sendChannel.send(embed=shopEmbed)
    except discord.Forbidden:
        await message.channel.send(":x: I can't DM you, " + message.author.display_name \
            + "! Please enable DMs from users who are not friends.")
        return
    if sendDM:
        await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)

bbCommands.register("loma", cmd_loma, 0, allowDM=True, helpSection="loma shop", signatureStr="**loma** *[item-type]*",
                    shortHelp="List all items currently on offer, to you only, by the pirates at Loma.",
                    longHelp="List all items currently on offer, to you only, by the pirates at Loma. Give an item type " \
                        + "(ship/weapon/turret/module/tool) to only list items of that type.")
