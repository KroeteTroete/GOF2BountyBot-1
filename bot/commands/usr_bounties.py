import discord
from datetime import datetime, timedelta

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import cfg, bbData
from ..gameObjects.battles import duelRequest
from ..scheduling import timedTask
from ..reactionMenus import reactionDuelChallengeMenu, expiryFunctions, confirmationReactionMenu
from ..users import basedUser, basedGuild
from ..gameObjects.items import shipItem
from ..gameObjects.items.weapons import primaryWeapon
from ..gameObjects.items.tools import crateTool
from ..databases.bountyDivision import BountyDivision
from ..databases.bountyDB import nameForDivision
from ..lib import gameMaths


botCommands.addHelpSection(0, "bounty hunting")


async def cmd_check(message : discord.Message, args : str, isDM : bool):
    """Check a system for bounties and handle rewards

    :param discord.Message message: the discord message calling the command
    :param str args: string containing one system to check
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # Verify that this guild has bounties enabled
    callingGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if callingGuild.bountiesDisabled:
        await message.channel.send(":x: This server does not have bounties enabled.")
        return

    # verify this is the calling user's home guild. If no home guild is set, transfer here.
    requestedBBUser = botState.usersDB.getOrAddID(message.author.id)
    if not requestedBBUser.hasHomeGuild():
        await requestedBBUser.transferGuild(message.guild)
        await message.channel.send(":airplane_arriving: Your home guild has been set.")
    elif requestedBBUser.homeGuildID != message.guild.id:
        await message.channel.send(":x: This command can only be used from your home guild!")
        return

    # verify a system was given
    if args == "":
        await message.channel.send(":x: Please provide a system to check! E.g: `" \
                                    + callingGuild.commandPrefix + "check Pescal Inartu`")
        return

    requestedSystem = args.title()
    systObj = None

    # attempt to find the requested system in the database
    for syst in bbData.builtInSystemObjs.keys():
        if bbData.builtInSystemObjs[syst].isCalled(requestedSystem):
            systObj = bbData.builtInSystemObjs[syst]

    # reject if the requested system is not in the database
    if systObj is None:
        if len(requestedSystem) < 20:
            await message.channel.send(":x: The **" + requestedSystem + "** system is not on my star map! :map:")
        else:
            await message.channel.send(":x: The **" + requestedSystem[0:15] + "**... system is not on my star map! :map:")
        return

    requestedSystem = systObj.name

    if not requestedBBUser.activeShip.hasWeaponsEquipped() and not requestedBBUser.activeShip.hasTurretsEquipped():
        await message.channel.send(":x: Your ship has no weapons equipped!")
        return

    # Restrict the number of bounties a player may win in a single day
    if requestedBBUser.bountyWinsToday and requestedBBUser.dailyBountyWinsReset < datetime.utcnow():
        requestedBBUser.bountyWinsToday = 0
        requestedBBUser.dailyBountyWinsReset = lib.timeUtil.tomorrow()

    if requestedBBUser.bountyWinsToday >= cfg.maxDailyBountyWins:
        await message.channel.send(":x: You have reached the maximum number of bounty wins allowed for today! " \
                                    + "Check back tomorrow.")
        return

    # ensure the calling user is not on checking cooldown
    if datetime.utcfromtimestamp(requestedBBUser.bountyCooldownEnd) < datetime.utcnow():
        bountyWon = False
        bountyLost = False
        systemInBountyRoute = False
        dailyBountiesMaxReached = False
        userLevel = gameMaths.calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP)
        # list of completed bounties to remove from the bounties database
        toPop = []
        toEscape = []
        btyDivision = callingGuild.bountiesDB.divisionForLevel(userLevel)
        sightedCriminalsStr = ""

        for tlBounties in btyDivision.bounties.values():
            for bounty in tlBounties.values():
                # Check the passed system in current bounty
                checkResult = bounty.check(requestedSystem, message.author.id)
                # If current bounty resides in the requested system
                if checkResult == 3:
                    duelResults = duelRequest.fightShips(requestedBBUser.activeShip, bounty.activeShip,
                                                            cfg.duelVariancePercent)
                    statsEmbed = lib.discordUtil.makeEmbed(authorName="**Duel Stats**")
                    statsEmbed.add_field(name="DPS (" + str(cfg.duelVariancePercent * 100) + "% RNG)",
                                            value=message.author.mention + ": " \
                                                + str(round(duelResults["ship1"]["DPS"]["varied"], 2)) + "\n" \
                                                + bounty.criminal.name + ": " \
                                                + str(round(duelResults["ship2"]["DPS"]["varied"], 2)))
                    statsEmbed.add_field(name="Health (" + str(cfg.duelVariancePercent * 100) + "% RNG)",
                                            value=message.author.mention + ": " \
                                                + str(round(duelResults["ship1"]["health"]["varied"])) + "\n" \
                                                + bounty.criminal.name + ": " \
                                                + str(round(duelResults["ship2"]["health"]["varied"], 2)))
                    statsEmbed.add_field(name="Time To Kill",
                                            value=message.author.mention + ": " \
                                                + (str(round(duelResults["ship1"]["TTK"], 2)) \
                                                    if duelResults["ship1"]["TTK"] != -1 else "inf.") + "s\n" \
                                                + bounty.criminal.name + ": " \
                                                + (str(round(duelResults["ship2"]["TTK"], 2)) \
                                                    if duelResults["ship2"]["TTK"] != -1 else "inf.") + "s")

                    if duelResults["winningShip"] is not requestedBBUser.activeShip:
                        toEscape.append(bounty)
                        # bounty.escape()
                        bountyLost = True
                        await message.channel.send(bounty.criminal.name + " got away! ", embed=statsEmbed)

                    else:
                        bountyWon = True
                        requestedBBUser.bountyWinsToday += 1
                        if not dailyBountiesMaxReached and requestedBBUser.bountyWinsToday >= cfg.maxDailyBountyWins:
                            requestedBBUser.dailyBountyWinsReset = lib.timeUtil.tomorrow()
                            dailyBountiesMaxReached = True

                        # reward all contributing users
                        rewards = bounty.calcRewards()
                        levelUpMsg = ""
                        for userID in rewards:
                            currentBBUser = botState.usersDB.getUser(userID)
                            currentBBUser.credits += rewards[userID]["reward"]
                            currentBBUser.lifetimeBountyCreditsWon += rewards[userID]["reward"]
                            currentDCUser = message.guild.get_member(currentBBUser.id)

                            oldLevel = gameMaths.calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
                            if oldLevel == cfg.maxTechLevel:
                                rewards[userID]["xp"] = 0
                                continue
                            
                            currentBBUser.bountyHuntingXP += rewards[userID]["xp"]

                            newLevel = gameMaths.calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
                            if newLevel > oldLevel:
                                levelUpCrate = bbData.builtInCrateObjs["levelUp"][newLevel]
                                currentBBUser.inactiveTools.addItem(levelUpCrate)
                                
                                oldDiv = callingGuild.bountiesDB.divisionForLevel(oldLevel)
                                newDiv = callingGuild.bountiesDB.divisionForLevel(newLevel)
                                if oldDiv is newDiv:
                                    levelUpMsg += "\n:arrow_up: **Level Up!**\n" \
                                                + lib.discordUtil.userOrMemberName(currentDCUser, message.guild) \
                                                + f" reached **Bounty Hunter Level {newLevel}!** :partying_face:\n" \
                                                + f"You got a **{levelUpCrate.name}**."
                                
                                else:
                                    oldDivName, newDivName = nameForDivision(oldDiv), nameForDivision(newDiv)
                                    levelUpMsg += "\n:arrow_double_up: **New Division Reached!** :sparkles:\n" \
                                                + lib.discordUtil.userOrMemberName(currentDCUser, message.guild) \
                                                + f" hit **Bounty Hunter Level {newLevel}**, and reached the " \
                                                + f"**{newDivName.title()} Division!** :partying_face:\n" \
                                                + f"You got a **{levelUpCrate.name}**."
                                
                                    if callingGuild.hasBountyAlertRoles:
                                        oldRole = message.guild.get_role(oldDiv.alertRoleID)
                                        newRole = None
                                        if oldRole is None:
                                            await message.channel.send(f":woozy_face: I can't find the {oldDivName.title()}" \
                                                                        + " division bounty alerts role, did it get deleted?")
                                                                        
                                        elif oldRole in message.author.roles:
                                            newRole = message.guild.get_role(newDiv.alertRoleID)
                                            if newRole is None:
                                                await message.channel.send(":woozy_face: I can't find the " \
                                                                        + f"{newDivName.title()} division's bounty alerts " \
                                                                        + "role, did it get deleted?")
                                        
                                        if oldRole is not None or newRole is not None:
                                            await callingGuild.levelUpSwapRoles(currentDCUser, message.channel, oldRole, newRole)

                        if levelUpMsg != "":
                            await message.channel.send(levelUpMsg)

                        # Announce the bounty has been completed
                        await callingGuild.announceBountyWon(bounty, rewards, message.author)
                        await message.channel.send("__Duel Statistics__",embed=statsEmbed)

                        # Raise guild's activity temperature for this bounty's tl
                        numContributingUsers = len(set(rewards))
                        btyDivision.raiseTemp(numContributingUsers * cfg.activityTempPerPlayer)

                        # add this bounty to the list of bounties to be removed
                        toPop.append(bounty)

                # Update routes in this division containing the checked system
                if checkResult in [2, 3]:
                    systemInBountyRoute = True
                    await callingGuild.updateBountyBoardChannel(bounty, bountyComplete=checkResult == 3)
                    # Check if any bounties are close to the requested system in their route, defined by cfg.closeBountyThreshold
                    if checkResult == 2 and \
                            0 < bounty.route.index(bounty.answer) - bounty.route.index(requestedSystem) < cfg.closeBountyThreshold:
                        # Print any close bounty names
                        sightedCriminalsStr += "\n**       **• Local security forces spotted **" \
                                                + lib.discordUtil.criminalNameOrDiscrim(bounty.criminal) \
                                                + "** here recently."

        # remove all completed bounties
        for bounty in toPop:
            btyDivision.removeBountyObj(bounty)
        # remove all escaped bounties
        for bounty in toEscape:
            bounty.escape()

        # If a bounty was won, print a congratulatory message
        if bountyWon:
            if dailyBountiesMaxReached:
                maxBountiesReachedMsg = "You have now reached the maximum number of bounty wins allowed for today! " \
                                            + "Please check back tomorrow."
            else:
                maxBountiesReachedMsg = "You have **" + str(cfg.maxDailyBountyWins - requestedBBUser.bountyWinsToday) \
                                        + "** remaining bounty wins today!"
            requestedBBUser.bountyWins += 1
            await message.channel.send(sightedCriminalsStr + "\n" + ":moneybag: **" + message.author.display_name \
                                        + "**, you now have **" + str(requestedBBUser.credits) + " Credits!**\n" \
                                        + maxBountiesReachedMsg)

        # If no bounty was won, print an error message
        elif not bountyLost:
            await message.channel.send(":telescope: **" + message.author.display_name \
                                        + "**, you did not find any criminals in **" + requestedSystem.title() \
                                        + "**!\n" + sightedCriminalsStr)

        # Only put the calling user on checking cooldown and increment systemsChecked stat if the system checked
        # is on an active bounty's route.
        if systemInBountyRoute:
            requestedBBUser.systemsChecked += 1
            # Put the calling user on checking cooldown
            requestedBBUser.bountyCooldownEnd = (datetime.utcnow() \
                                                + timedelta(minutes=cfg.timeouts.checkCooldown["minutes"])).timestamp()

    # If the calling user is on checking cooldown
    else:
        # Print an error message with the remaining time on the calling user's cooldown
        diff = datetime.utcfromtimestamp(botState.usersDB.getUser(message.author.id).bountyCooldownEnd) - datetime.utcnow()
        await message.channel.send(":stopwatch: **" + message.author.display_name \
                                    + "**, your *Khador Drive* is still charging! please wait **" \
                                    + lib.timeUtil.td_format_noYM(diff) + ".**")

botCommands.register("check", cmd_check, 0, aliases=["search"], allowDM=False, helpSection="bounty hunting",
                        signatureStr="**check <system>**",
                        shortHelp="Check if any criminals are in the given system, arrest them, and get paid! 💰" \
                        + "\n🌎 This command must be used in your **home server**.")


async def cmd_bounties(message: discord.Message, args: str, isDM: bool):
    """List a summary of all currently active bounties in one division.
    If no division is specified, the calling user's division is used.
    Division can be specified either as a number (a tech level), or a division name as given in cfg.bountyDivisions

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a division name or tech level
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # Verify that this guild has bounties enabled
    callingGuild = botState.guildsDB.getGuild(message.guild.id)
    if callingGuild.bountiesDisabled:
        await message.channel.send(":x: This server does not have bounties enabled.")
        return

    division: BountyDivision = None

    if not args:
        try:
            callingUser = botState.usersDB.getUser(message.author.id)
        except KeyError:
            division = callingGuild.bountiesDB.divisionForLevel(0)
        else:
            userLevel = gameMaths.calculateUserBountyHuntingLevel(callingUser.bountyHuntingXP)
            division = callingGuild.bountiesDB.divisionForLevel(userLevel)
    else:
        if lib.stringTyping.isInt(args):
            try:
                division = callingGuild.bountiesDB.divisionForLevel(int(args))
            except KeyError:
                await message.reply(":x: Unknown division. You can either give a difficulty level (1-10), or a division name: " \
                                    + ", ".join(i.title() for i in list(cfg.bountyDivisions.keys())[:-1]) + " or " \
                                    + list(cfg.bountyDivisions.keys())[-1])
                return
        else:
            try:
                division = callingGuild.bountiesDB.divisionForName(args)
            except KeyError:
                await message.reply(":x: Unknown division. You can either give a difficulty level (1-10), or a division name: " \
                                    + ", ".join(i.title() for i in list(cfg.bountyDivisions.keys())[:-1]) + " or " \
                                    + list(cfg.bountyDivisions.keys())[-1])
                return

    divName = nameForDivision(division).title()

    if division.isEmpty():
        await message.channel.send(":stopwatch: There are no " + divName \
                                        + " division bounties active currently!\nYou have **" \
                                        + str(cfg.maxDailyBountyWins \
                                            - botState.usersDB.getOrAddID(message.author.id).bountyWinsToday) \
                                        + "** remaining bounty wins today.")
        return
    
    msgEmbed = discord.Embed(title=f"Active Bounties: {divName} Division",
                                description=f"Difficulty levels {division.minLevel} - {division.maxLevel} ~ Times given in UTC",
                                colour=discord.Colour.random())
    msgEmbed.set_footer(icon_url=bbData.rocketIcon,
                        text="Track down criminals and win credits using " + callingGuild.commandPrefix + "route " \
                                + "and " + callingGuild.commandPrefix + "check!")

    # Collect and print summaries of all active bounties
    for tl in division.bounties:
        if division.bounties[tl]:
            msgEmbed.add_field(name="​", value=f"__Level {tl}__", inline=False)
            for crim, bounty in division.bounties[tl].items():
                timeLeft = datetime.utcfromtimestamp(bounty.endTime) - datetime.utcnow()
                if bounty.faction in bbData.bountyFactionEmojis:
                    factionEmoji = lib.emojis.BasedEmoji(id=bbData.bountyFactionEmojis[bounty.faction]).sendable + " "
                else:
                    factionEmoji = ""
                msgEmbed.add_field(name=factionEmoji + lib.discordUtil.criminalNameOrDiscrim(crim),
                                    value=f"• {int(bounty.reward)} Credits\n"
                                            + f"• {len(bounty.route)} possible systems\n" \
                                            + f"• Ending in {lib.timeUtil.td_format_noYM(timeLeft)}")

    # Restrict the number of bounties a player may win in a single day
    if botState.usersDB.idExists(message.author.id):
        requestedBBUser = botState.usersDB.getUser(message.author.id)
        if requestedBBUser.dailyBountyWinsReset < datetime.utcnow():
            requestedBBUser.bountyWinsToday = 0
            requestedBBUser.dailyBountyWinsReset = lib.timeUtil.tomorrow()
        if requestedBBUser.bountyWinsToday >= cfg.maxDailyBountyWins:
            txtMsg = "\nYou have reached the maximum number of bounty wins allowed for today! Check back tomorrow."
        else:
            txtMsg = "\nYou have **" + str(cfg.maxDailyBountyWins - requestedBBUser.bountyWinsToday) \
                    + "** remaining bounty wins today."
    else:
        txtMsg = ""
    
    await message.channel.send(txtMsg, embed=msgEmbed)


botCommands.register("bounties", cmd_bounties, 0, allowDM=False, helpSection="bounty hunting",
                        signatureStr="**bounties** *[level or division]*",
                        shortHelp="List all active bounties in your division, or the one specified",
                        longHelp="If no division is given, name all currently active bounties. In your division.\n" \
                                    + "If a division is given, show all bountis in that division.\n"
                                    + "Division can be given either as a name, or as a difficulty level in that division.")


async def cmd_route(message : discord.Message, args : str, isDM : bool):
    """Display the current route of the requested criminal

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a criminal name or alias
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # Verify that this guild has bounties enabled
    callingGuild = botState.guildsDB.getGuild(message.guild.id)
    if callingGuild.bountiesDisabled:
        await message.channel.send(":x: This server does not have bounties enabled.")
        return

    # verify a criminal was specified
    if args == "":
        await message.channel.send(":x: Please provide the criminal name! E.g: `" + callingGuild.commandPrefix \
                                    + "route Kehnor`")
        return

    requestedBountyName = args
    # if the named criminal is wanted
    if callingGuild.bountiesDB.bountyNameExists(requestedBountyName.lower()):
        # display their route
        bounty = callingGuild.bountiesDB.getBounty(requestedBountyName.lower())
        outmessage = "**" + lib.discordUtil.criminalNameOrDiscrim(bounty.criminal) + "**'s current route:\n> "
        for system in bounty.route:
            outmessage += " " + ("~~" if bounty.checked[system] != -1 else "") \
                            + system + ("~~" if bounty.checked[system] != -1 else "") + ","
        outmessage = outmessage[:-1] + ". :rocket:"
        await message.channel.send(outmessage)
    # if the named criminal is not wanted
    else:
        # display an error
        outmsg = ":x: That pilot isn't on any bounty boards! :clipboard:"
        # accept user name + discrim instead of tags to avoid mention spam
        if lib.stringTyping.isMention(requestedBountyName):
            outmsg += "\n:warning: **Don't tag users**, use their name and ID number like so: `" \
                        + callingGuild.commandPrefix + "route Trimatix#2244`"
        await message.channel.send(outmsg)

botCommands.register("route", cmd_route, 0, allowDM=False, helpSection="bounty hunting", signatureStr="**route <criminal name>**",
                        shortHelp="Get the named criminal's current route.",
                        longHelp="Get the named criminal's current route.\n" \
                                    + "For a list of aliases for a given criminal, see `info criminal`.")


async def cmd_duel(message : discord.Message, args : str, isDM : bool):
    """⚠ WARNING: MARKED FOR CHANGE ⚠
    The following function is provisional and marked as planned for overhaul.
    Details: Overhaul is part-way complete, with a few fighting algorithm provided in gameObjects.items.battles.
    However, printing the fight details is yet to be implemented.
    This is planned to be done using simple message editing-based animation of player ships and progress bars for health etc.
    This command is functional for now, but the output is subject to change.

    Challenge another player to a duel, with an amount of credits as the stakes.
    The winning user is given stakes credits, the loser has stakes credits taken away.
    give 'challenge' to create a new duel request.
    give 'cancel' to cancel an existing duel request.
    give 'accept' to accept another user's duel request targetted at you.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the action (challenge/cancel/accept), a target user (mention or ID), and the stakes
                        (int amount of credits). stakes are only required when "challenge" is specified.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) == 0:
        await message.channel.send(":x: Please provide an action (`challenge`/`cancel`/`accept`/`reject or decline`), " \
                                    + "a user, and the stakes (an amount of credits)!")
        return
    action = argsSplit[0]
    if action not in ["challenge", "cancel", "accept", "reject", "decline"]:
        await message.channel.send(":x: Invalid action! please choose from `challenge`, `cancel`, " \
                                    + "`reject/decline` or `accept`.")
        return
    if action == "challenge":
        if len(argsSplit) < 3:
            await message.channel.send(":x: Please provide a user and the stakes (an amount of credits)!")
            return
    else:
        if len(argsSplit) < 2:
            await message.channel.send(":x: Please provide a user!")
            return
    requestedUser = lib.discordUtil.getMemberByRefOverDB(argsSplit[1], dcGuild=message.guild)
    if requestedUser is None:
        await message.channel.send(":x: User not found!")
        return
    if requestedUser.id == message.author.id:
        await message.channel.send(":x: You can't challenge yourself!")
        return
    if action == "challenge" and (not lib.stringTyping.isInt(argsSplit[2]) or int(argsSplit[2]) < 0):
        await message.channel.send(":x: Invalid stakes (amount of credits)!")
        return

    sourceBBUser = botState.usersDB.getOrAddID(message.author.id)
    targetBBUser = botState.usersDB.getOrAddID(requestedUser.id)

    callingGuild = botState.guildsDB.getGuild(message.guild.id)

    if action == "challenge":
        stakes = int(argsSplit[2])
        if sourceBBUser.hasDuelChallengeFor(targetBBUser):
            await message.channel.send(":x: You already have a duel challenge pending for " \
                                        + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                        + "! To make a new one, cancel it first. (see `" + callingGuild.commandPrefix \
                                        + "help duel`)")
            return

        try:
            newDuelReq = duelRequest.DuelRequest(
                sourceBBUser, targetBBUser, stakes, None, botState.guildsDB.getGuild(message.guild.id))
            duelTT = timedTask.TimedTask(expiryDelta=timedelta(**cfg.timeouts.duelRequest),
                                            expiryFunction=duelRequest.expireAndAnnounceDuelReq,
                                            expiryFunctionArgs={"duelReq": newDuelReq})
            newDuelReq.duelTimeoutTask = duelTT
            botState.duelRequestTTDB.scheduleTask(duelTT)
            sourceBBUser.addDuelChallenge(newDuelReq)
        except KeyError:
            await message.channel.send(":x: User not found! Did they leave the server?")
            return
        except Exception:
            await message.channel.send(":woozy_face: An unexpected error occurred! Tri, what did you do...")
            return

        expiryTimesSplit = duelTT.expiryTime.strftime("%d %B %H %M").split(" ")
        duelExpiryTimeString = "This duel request will expire on the **" + expiryTimesSplit[0].lstrip('0') \
                                + lib.stringTyping.getNumExtension(int(expiryTimesSplit[0])) + "** of **" \
                                + expiryTimesSplit[1] + "**, at **" + expiryTimesSplit[2] + ":" + expiryTimesSplit[3] \
                                + "** UTC."

        sentMsgs = []

        async def queueChallengeMsg(channel, challengerStr, targetStr):
            sentMsgs.append(await channel.send(":crossed_swords: **" + challengerStr + "** challenged " + targetStr \
                                                + " to duel for **" + str(stakes) + " Credits!**\nType `" \
                                                + callingGuild.commandPrefix + "duel accept " + str(message.author.id) \
                                                + "` (or `" + callingGuild.commandPrefix + "duel accept @" \
                                                + message.author.name + "` if you're in the same server) " \
                                                + "To accept the challenge!\n" + duelExpiryTimeString))

        if message.guild.get_member(requestedUser.id) is None:
            targetUserDCGuild = lib.discordUtil.findBBUserDCGuild(targetBBUser)
            if targetUserDCGuild is None:
                await message.channel.send(":x: User not found! Did they leave the server?")
                return
            else:
                targetUserBBGuild = botState.guildsDB.getGuild(targetUserDCGuild.id)
                if targetUserBBGuild.hasPlayChannel():
                    targetUserNameOrTag = lib.discordUtil.IDAlertedUserMentionOrName("duels_challenge_incoming_new",
                                                                                        dcGuild=targetUserDCGuild,
                                                                                        basedGuild=targetUserBBGuild,
                                                                                        dcUser=requestedUser,
                                                                                        basedUser=targetBBUser)
                    await queueChallengeMsg(targetUserBBGuild.getPlayChannel(), str(message.author), targetUserNameOrTag)
            await queueChallengeMsg(message.channel, message.author.mention, str(requestedUser))
        else:
            targetUserNameOrTag = lib.discordUtil.IDAlertedUserMentionOrName("duels_challenge_incoming_new",
                                                                                dcGuild=message.guild, dcUser=requestedUser,
                                                                                basedUser=targetBBUser)
            await queueChallengeMsg(message.channel, message.author.mention, targetUserNameOrTag)

        for msg in sentMsgs:
            menuTT = timedTask.TimedTask(expiryDelta=timedelta(**cfg.timeouts.duelChallengeMenuExpiry),
                                            expiryFunction=expiryFunctions.removeEmbedAndOptions, expiryFunctionArgs=msg.id)
            botState.reactionMenusTTDB.scheduleTask(menuTT)
            newMenu = reactionDuelChallengeMenu.ReactionDuelChallengeMenu(msg, newDuelReq, timeout=menuTT)
            newDuelReq.menus.append(newMenu)
            await newMenu.updateMessage()
            botState.reactionMenusDB[msg.id] = newMenu


    elif action == "cancel":
        if not sourceBBUser.hasDuelChallengeFor(targetBBUser):
            await message.channel.send(":x: You do not have an active duel challenge for this user! Did it already expire?")
            return

        if message.guild.get_member(requestedUser.id) is None:
            await message.channel.send(":white_check_mark: You have cancelled your duel challenge for **" \
                                        + str(requestedUser) + "**.")
            targetUserGuild = lib.discordUtil.findBBUserDCGuild(targetBBUser)
            if targetUserGuild is not None:
                targetUserBBGuild = botState.guildsDB.getGuild(targetUserGuild.id)
                if targetUserBBGuild.hasPlayChannel() and \
                        targetBBUser.isAlertedForID("duels_challenge_incoming_cancel", targetUserGuild, targetUserBBGuild,
                                                    targetUserGuild.get_member(targetBBUser.id)):
                    await targetUserBBGuild.getPlayChannel().send(":shield: " + requestedUser.mention + ", " \
                                                                    + str(message.author) \
                                                                    + " has cancelled their duel challenge.")
        else:
            if targetBBUser.isAlertedForID("duels_challenge_incoming_cancel", message.guild,
                                            botState.guildsDB.getGuild(message.guild.id),
                                            message.guild.get_member(targetBBUser.id)):
                await message.channel.send(":white_check_mark: You have cancelled your duel challenge for " \
                                            + requestedUser.mention + ".")
            else:
                await message.channel.send(":white_check_mark: You have cancelled your duel challenge for **" \
                                            + str(requestedUser) + "**.")

        # IDAlertedUserMentionOrName(alertType, dcUser=None, basedUser=None, basedGuild=None, dcGuild=None)
        for menu in sourceBBUser.duelRequests[targetBBUser].menus:
            await menu.delete()
        await sourceBBUser.duelRequests[targetBBUser].duelTimeoutTask.forceExpire(callExpiryFunc=False)
        sourceBBUser.removeDuelChallengeTarget(targetBBUser)

    elif action in ["reject", "decline"]:
        if not targetBBUser.hasDuelChallengeFor(sourceBBUser):
            await message.channel.send(":x: This user does not have an active duel challenge for you! Did it expire?")
            return

        duelReq = targetBBUser.duelRequests[sourceBBUser]
        await duelRequest.rejectDuel(duelReq, message, requestedUser, message.author)

    elif action == "accept":
        if not targetBBUser.hasDuelChallengeFor(sourceBBUser):
            await message.channel.send(":x: This user does not have an active duel challenge for you! Did it expire?")
            return

        requestedDuel = targetBBUser.duelRequests[sourceBBUser]

        if sourceBBUser.credits < requestedDuel.stakes:
            await message.channel.send(":x: You do not have enough credits to accept this duel request! (" \
                                        + str(requestedDuel.stakes) + ")")
            return
        if targetBBUser.credits < requestedDuel.stakes:
            await message.channel.send(":x:" + str(requestedUser) + " does not have enough credits to fight this duel! (" \
                                        + str(requestedDuel.stakes) + ")")
            return

        await duelRequest.fightDuel(message.author, requestedUser, requestedDuel, message)

botCommands.register("duel", cmd_duel, 0, forceKeepArgsCasing=True, allowDM=False, helpSection="bounty hunting",
                        signatureStr="**duel [action] [user]** *<stakes>*",
                        shortHelp="Fight other players! Action can be `challenge`, `cancel`, `accept` or `reject`.",
                        longHelp="Fight other players! Action can be `challenge`, `cancel`, `accept` or `reject`. " \
                                    + "When challenging another user to a duel, you must give the amount of credits " \
                                    + "you will win - the 'stakes'.")


async def cmd_use(message : discord.Message, args : str, isDM : bool):
    """Use the specified tool from the user's inventory.

    :param discord.Message message: the discord message calling the command
    :param str args: a single integer indicating the index of the tool to use
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    callingBUser = botState.usersDB.getOrAddID(message.author.id)
    callingGuild = botState.guildsDB.getGuild(message.guild.id)

    if not lib.stringTyping.isInt(args):
        await message.channel.send(":x: Please give the number of the tool you would like to use! e.g: `" \
                                    + callingGuild.commandPrefix + "use 1`")
    else:
        toolNum = int(args)
        if toolNum < 1:
            await message.channel.send(":x: Tool number must be at least 1!")
        elif callingBUser.inactiveTools.isEmpty():
            await message.channel.send(":x: You don't have any tools to use!")
        elif toolNum > callingBUser.inactiveTools.numKeys:
            await message.channel.send(":x: Tool number too big - you only have " + str(callingBUser.inactiveTools.numKeys) \
                                        + " tool" + ("" if callingBUser.inactiveTools.numKeys == 1 else "s") + "!")
        else:
            result = await callingBUser.inactiveTools[toolNum - 1].item.userFriendlyUse(message, ship=callingBUser.activeShip,
                                                                                        callingBUser=callingBUser)
            await message.channel.send(result)


botCommands.register("use", cmd_use, 0, allowDM=False, helpSection="bounty hunting", signatureStr="**use [tool number]**",
                        shortHelp="Use the tool in your hangar with the given number. See `hangar` for tool numbers.",
                        longHelp="Use the tool in your hangar with the given number. Tool numbers can be seen next your " \
                                    + "items in `hangar tool`. For example, if tool number `1` is a ship skin, `use 1` will" \
                                    + " apply the skin to your active ship.")


async def cmd_prestige(message : discord.Message, args : str, isDM : bool):
    """Reset the calling user's bounty hunter xp to zero and remove all of their items.
    Can only be used by level 10 bounty hunters.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not botState.usersDB.idExists(message.author.id):
        await message.channel.send(":x: This command can only be used by level 10 bounty hunters!")
        return

    callingBBUser = botState.usersDB.getUser(message.author.id)
    if gameMaths.calculateUserBountyHuntingLevel(callingBBUser.bountyHuntingXP) < 10:
        await message.channel.send(":x: This command can only be used by level 10 bounty hunters!")
        return

    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix

    confirmMsg = await message.channel.send("Are you sure you want to prestige now? Your bounty hunter level, loadout, " \
                                            + "balance, hangar and loma will all be **reset**.\n" \
                                            + "You will be awarded with a ship upgrade, and a special skins crate!\n" \
                                            + "You can save items from being removed by storing them in `" \
                                            + commandPrefix + "kaamo`, but you will not be able to retreive your " \
                                            + "items until you reach level 10.")
    confirmResult = await confirmationReactionMenu.InlineConfirmationMenu(confirmMsg, message.author,
                                                                            cfg.prestigeConfirmTimeoutSeconds).doMenu()

    if cfg.defaultEmojis.accept in confirmResult:
        callingBBUser.bountyHuntingXP = gameMaths.bountyHuntingXPForLevel(1)
        callingBBUser.activeShip = shipItem.Ship.fromDict(basedUser.defaultShipLoadoutDict)
        callingBBUser.credits = 0
        callingBBUser.inactiveShips.clear()
        callingBBUser.inactiveModules.clear()
        callingBBUser.inactiveWeapons.clear()
        for weaponDict in basedUser.defaultUserDict["inactiveWeapons"]:
            callingBBUser.inactiveWeapons.addItem(primaryWeapon.PrimaryWeapon.fromDict(weaponDict["item"]),
                                                    quantity=weaponDict["count"])
        callingBBUser.inactiveTurrets.clear()
        callingBBUser.inactiveTools.clear()
        if callingBBUser.loma is not None:
            callingBBUser.loma.shipsStock.clear()
            callingBBUser.loma.weaponsStock.clear()
            callingBBUser.loma.modulesStock.clear()
            callingBBUser.loma.turretsStock.clear()
            callingBBUser.loma.toolsStock.clear()

        callingBBUser.prestiges += 1
        newCrate = crateTool.CrateTool.fromDict({"type": "bbCrate", "crateType": "special", "typeNum": 0, "builtIn": True})
        callingBBUser.inactiveTools.addItem(newCrate)

        await message.channel.send(":astronaut: **" + lib.discordUtil.userOrMemberName(message.author, message.guild) \
                                    + " prestiged!** :tada:\n • You got a **" + newCrate.name + "!**")
    else:
        await message.channel.send("🛑 Prestige cancelled.")


botCommands.register("prestige", cmd_prestige, 0, helpSection="bounty hunting", signatureStr="**prestige**",
                        shortHelp="Reset your items and bounty hunting XP, in exchange for a ship upgrade! " \
                            + "Command unlocked at level 10. Kaamo items are saved.",
                        longHelp="Reset your save data, including your bounty hunter level, loadout, balance, hangar and " \
                            + "loma. You will be awarded with a ship upgrade available in Loma!\n\n" \
                            + "You can save items from being removed by first storing them in `Kaamo`. Items stored in " \
                            + "`Kaamo` will be made accessible again once you reach level 10!")
