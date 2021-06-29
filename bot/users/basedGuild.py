from __future__ import annotations
from discord import Embed, channel, Client, Forbidden, Guild, Member, Message, HTTPException, NotFound, Colour, Role
from discord import TextChannel
from typing import List, Dict, Union
from datetime import timedelta
import asyncio
from aiohttp import client_exceptions
import traceback
import random

from .. import botState, lib
from ..gameObjects import guildShop
from ..databases.bountyDB import BountyDB, nameForDivision
from ..userAlerts import userAlerts
from ..cfg import cfg, bbData
from ..scheduling.timedTask import TimedTask, DynamicRescheduleTask
from ..gameObjects.bounties import bounty, bountyConfig
from ..baseClasses import serializable
from . import guildActivity
from ..databases import bountyDivision


class BasedGuild(serializable.Serializable):
    """A class representing a guild in discord, and storing extra bot-specific information about it.

    :var id: The ID of the guild, directly corresponding to a discord guild's ID.
    :vartype id: int
    :var dcGuild: This guild's corresponding discord.Guild object
    :vartype dcGuild: discord.Guild
    :var announceChannel: The discord.channel object for this guild's announcements chanel.
                            None when no announce channel is set for this guild.
    :vartype announceChannel: discord.channel.TextChannel
    :var playChannel: The discord.channel object for this guild's bounty playing chanel.
                        None when no bounty playing channel is set for this guild.
    :vartype playChannel: discord.channel.TextChannel
    :var shop: This guild's guildShop object
    :vartype shop: guildShop
    :var alertRoles: A dictionary of user alert IDs to guild role IDs.
    :vartype alertRoles: dict[str, int]
    :var hasBountyBoardChannels: Whether this guild has bounty board channels for each of its divisions or not
    :vartype hasBountyBoardChannel: bool
    :var ownedRoleMenus: The number of ReactionRolePickers present in this guild
    :vartype ownedRoleMenus: int
    :var bounties: This guild's active bounties
    :vartype bounties: BountyDB
    :var bountiesDisabled: Whether or not to disable this guild's bountyDB and bounty spawning
    :vartype bountiesDisabled: bool
    :var shopDisabled: Whether or not to disable this guild's guildShop and shop refreshing
    :vartype shopDisabled: bool
    :var hasBountyAlertRoles: True if the guild has alert roles for each of its divisions, False otherwise
    :vartype hasBountyAlertRoles: bool
    """

    def __init__(self, id: int, dcGuild: Guild, bounties: BountyDB, commandPrefix: str = cfg.defaultCommandPrefix,
            announceChannel : channel.TextChannel = None, playChannel : channel.TextChannel = None,
            shop : guildShop.TechLeveledShop = None,
            alertRoles : Dict[str, int] = {}, ownedRoleMenus : int = 0, bountiesDisabled : bool = False,
            shopDisabled : bool = False):
        """
        :param int id: The ID of the guild, directly corresponding to a discord guild's ID.
        :param discord.Guild dcGuild: This guild's corresponding discord.Guild object
        :param BountyDB bounties: This guild's active bounties
        :param discord.channel announceChannel: The discord.channel object for this guild's announcements chanel.
                                                None when no announce channel is set for this guild.
        :param discord.channel playChannel: The discord.channel object for this guild's bounty playing chanel.
                                            None when no bounty playing channel is set for this guild.
        :param guildShop shop: This guild's guildShop object
        :param dict[str, int] alertRoles: A dictionary of user alert IDs to guild role IDs.
        :param int ownedRoleMenus: The number of ReactionRolePickers present in this guild
        :param bool bountiesDisabled: Whether or not to disable this guild's bountyDB and bounty spawning
        :param bool shopDisabled: Whether or not to disable this guild's guildShop and shop refreshing
        :raise TypeError: When given an incompatible argument type
        """

        if dcGuild is None:
            raise lib.exceptions.NoneDCGuildObj("Given dcGuild of type '" + type(dcGuild).__name__ \
                                                + "', expecting discord.Guild")

        self.id = id
        self.dcGuild = dcGuild
        if not commandPrefix:
            raise ValueError("Empty command prefix provided")
        self.commandPrefix = commandPrefix

        if type(id) == float:
            id = int(id)
        elif type(id) != int:
            raise TypeError("id must be int, given " + str(type(id)))

        self.announceChannel = announceChannel
        self.playChannel = playChannel

        self.shopDisabled = shopDisabled
        if shopDisabled:
            self.shop = None
        else:
            self.shop = guildShop.TechLeveledShop() if shop is None else shop

        self.alertRoles = {}
        for alertID in userAlerts.userAlertsIDsTypes.keys():
            if issubclass(userAlerts.userAlertsIDsTypes[alertID], userAlerts.GuildRoleUserAlert):
                self.alertRoles[alertID] = alertRoles[alertID] if alertID in alertRoles else -1

        self.ownedRoleMenus = ownedRoleMenus
        self.bountiesDB = bounties
        self.bountiesDisabled = bountiesDisabled

        if bountiesDisabled:
            self.hasBountyBoardChannels = False
            self.hasBountyAlertRoles = False
        else:
            try:
                self.hasBountyBoardChannels = self.bountiesDB.divisionForLevel(cfg.minTechLevel).bountyBoardChannel is not None
            except AttributeError:
                self.hasBountyBoardChannels = False

            try:
                self.hasBountyAlertRoles = self.bountiesDB.divisionForLevel(cfg.minTechLevel).alertRoleID != -1
            except AttributeError:
                self.hasBountyAlertRoles = False


    async def makeBountyAlertRoles(self):
        """Create a set of new roles to ping when bounties are created.

        :raise ValueError: If the guild already has new bounty alert roles set, or has bounties disabled
        :raise Forbidden: If the bot does not have role creation permissions
        :raise HTTPException: If creation of any role failed
        :raise RuntimeError: If any roles failed to create for some unexpected reason
        """
        if self.hasBountyAlertRoles:
            raise ValueError("This guild already has bounty alert roles")
        if self.bountiesDisabled:
            raise ValueError("This guild has bounties disabled")
        roleMakers = set()
        divsDone = set()
        async def makeDivRole(div: bountyDivision.BountyDivision):
            divsDone.add(div)
            divName = nameForDivision(div)
            newRole = await self.dcGuild.create_role(name=f"{divName.title()} Bounty Hunter",
                                                    colour=Colour.from_rgb(*cfg.defaultBountyAlertRoleColours[divName]),
                                                    reason="Creating new bounty alert roles requested by BB command")
            div.alertRoleID = newRole.id
        for div in self.bountiesDB.divisions.values():
            task = asyncio.create_task(makeDivRole(div))
            roleMakers.add(task)

        await asyncio.wait(roleMakers)
        for task in roleMakers:
            if e := task.exception():
                for doneDiv in divsDone:
                    doneDiv.alertRoleID = -1
                raise e
        for div in self.bountiesDB.divisions.values():
            if div.alertRoleID == -1:
                for doneDiv in self.bountiesDB.divisions.values():
                    doneDiv.alertRoleID = -1
                raise RuntimeError("An unknown error occurred when creating roles")
        
        self.hasBountyAlertRoles = True


    async def deleteBountyAlertRoles(self):
        """Delete the bounty alert roles from the server.

        :raise ValueError: If the guild does not have new bounty alert roles set
        :raise Forbidden: If the bot does not have role deletion permissions
        :raise HTTPException: If deletion of any role failed
        """
        if not self.hasBountyAlertRoles:
            raise ValueError("This guild does not have bounty alert roles")
        roleRemovers = set()
        async def removeDivRole(div: bountyDivision.BountyDivision):
            if div.alertRoleID != -1:
                tlRole = self.dcGuild.get_role(div.alertRoleID)
                if tlRole is None:
                    await self.dcGuild.fetch_roles()
                tlRole = self.dcGuild.get_role(div.alertRoleID)
                if tlRole is not None:
                    await tlRole.delete(reason="Removing new bounty alert roles requested by BB command")
                div.alertRoleID = -1
        for div in self.bountiesDB.divisions.values():
            task = asyncio.create_task(removeDivRole(div))
            roleRemovers.add(task)
        await asyncio.wait(roleRemovers)
        for task in roleRemovers:
            if e := task.exception():
                raise e

        self.hasBountyAlertRoles = False


    async def levelUpSwapRoles(self, dcUser: Member, channel: TextChannel, oldRole: Role, newRole: Role):
        """Remove oldRole from dcUser, and grant newRole.
        If errors occur, they will be printed in the context of dcUser leveling up their bounty Hunting level,
        and sent in channel. If oldRole or newRole are given as None, they will be ignored and no exception raised.

        :param Member dcUser: The user to toggle roles for
        :param TextChannel channel: The channel in which to send errors
        :param Role oldRole: The role to remove, corresponding to dcUser's previous tech level
        :param Role newRole: The role to grant, corresponding to dcUser's new tech level
        """
        if oldRole is not None:
            try:
                await dcUser.remove_roles(oldRole, reason="User leveled up into a new division")
            except Forbidden:
                await channel.send(":woozy_face: I don't have permission to remove your old division role! Please ensure " \
                                    + "it is beneath the BountyBot role.")
            except HTTPException as e:
                await channel.send(":woozy_face: Something went wrong when removing your old division role!\n" \
                                    + "The error has been logged.")
                botState.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to remove new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category="userAlerts", exception=e)
            except client_exceptions.ClientOSError as e:
                await channel.send(":thinking: Whoops! A connection error occurred when removing your old division role, " \
                                    + "the error has been logged.")
                botState.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to remove new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category="userAlerts", exception=e)
        if newRole is not None:
            try:
                await dcUser.add_roles(newRole, reason="User leveled up into a new division")
            except Forbidden:
                await channel.send(":woozy_face: I don't have permission to grant your new division role! Please ensure " \
                                    + "it is beneath the BountyBot role.")
            except HTTPException as e:
                await channel.send(":woozy_face: Something went wrong when granting your new division role!\n" \
                                    + "The error has been logged.")
                botState.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to grant new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category="userAlerts", exception=e)
            except client_exceptions.ClientOSError:
                await channel.send(":thinking: Whoops! A connection error occurred when granting your new division role, " \
                                    + "the error has been logged.")
                botState.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to grant new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category="userAlerts", exception=e)


    def getAnnounceChannel(self) -> channel.TextChannel:
        """Get the discord channel object of the guild's announcements channel.

        :return: the discord.channel of the guild's announcements channel
        :rtype: discord.channel.TextChannel
        :raise ValueError: If this guild does not have an announcements channel
        """
        if not self.hasAnnounceChannel():
            raise ValueError("This guild has no announce channel set")
        return self.announceChannel


    def getPlayChannel(self) -> channel.TextChannel:
        """Get the discord channel object of the guild's bounty playing channel.

        :return: the discord channel object of the guild's bounty playing channel
        :raise ValueError: If this guild does not have a play channel
        :rtype: discord.channel.TextChannel
        """
        if not self.hasPlayChannel():
            raise ValueError("This guild has no play channel set")
        return self.playChannel


    def setAnnounceChannel(self, announceChannel : channel.TextChannel):
        """Set the discord channel object of the guild's announcements channel.

        :param int announceChannel: The discord channel object of the guild's new announcements channel
        """
        self.announceChannel = announceChannel


    def setPlayChannel(self, playChannel : channel.TextChannel):
        """Set the discord channel of the guild's bounty playing channel.

        :param int playChannel: The discord channel object of the guild's new bounty playing channel
        """
        self.playChannel = playChannel


    def hasAnnounceChannel(self) -> bool:
        """Whether or not this guild has an announcements channel

        :return: True if this guild has a announcements channel, False otherwise
        :rtype bool:
        """
        return self.announceChannel is not None


    def hasPlayChannel(self) -> bool:
        """Whether or not this guild has a play channel

        :return: True if this guild has a play channel, False otherwise
        :rtype bool:
        """
        return self.playChannel is not None


    def removePlayChannel(self):
        """Remove and deactivate this guild's announcements channel.

        :raise ValueError: If this guild does not have a play channel
        """
        if not self.hasPlayChannel():
            raise ValueError("Attempted to remove play channel on a BasedGuild that has no playChannel")
        self.playChannel = None


    def removeAnnounceChannel(self):
        """Remove and deactivate this guild's play channel.

        :raise ValueError: If this guild does not have an announcements channel
        """
        if not self.hasAnnounceChannel():
            raise ValueError("Attempted to remove announce channel on a BasedGuild that has no announceChannel")
        self.announceChannel = None


    def getUserAlertRoleID(self, alertID : str) -> int:
        """Get the ID of this guild's alerts role for the given alert ID.

        :param str alertID: The alert ID for which the role ID should be fetched
        :return: The ID of the discord role that this guild mentions for the given alert ID.
        :rtype: int
        """
        return self.alertRoles[alertID]


    def setUserAlertRoleID(self, alertID : str, roleID : int):
        """Set the ID of this guild's alerts role for the given alert ID.

        :param str alertID: The alert ID for which the role ID should be set
        :param int roleID: The ID of the role which this guild should mention when alerting alertID
        """
        self.alertRoles[alertID] = roleID


    def removeUserAlertRoleID(self, alertID : str):
        """Remove the stored role and deactivate alerts for the given alertID

        :param str alertID: The alert ID for which the role ID should be removed
        """
        self.alertRoles[alertID] = -1


    def hasUserAlertRoleID(self, alertID : str) -> bool:
        """Decide whether or not this guild has a role set for the given alert ID.

        :param str alertID: The alert ID for which the role existence should be tested
        :return: True if this guild has a role set to mention for alertID
        :rtype: bool
        :raise KeyError: If given an unrecognised alertID
        """
        if alertID in self.alertRoles:
            return self.alertRoles[alertID] != -1
        raise KeyError("Unknown GuildRoleUserAlert ID: " + alertID)


    async def makeBountyBoardChannelMessage(self, bounty : bounty.Bounty, msg : str = "", embed : Embed = None) -> Message:
        """Create a new bountyBoardChannel listing for the given bounty, in the given guild.
        guild must own a bountyBoardChannel.

        :param bounty.Bounty bounty: The bounty for which to create a listing
        :param str msg: The text to display in the listing message content (Default "")
        :param discord.Embed embed: The embed to display in the listing message - this will be removed immediately in place
                                    of the embed generated during bountyBoardChannel.updateBountyMessage,
                                    so is only really useful in case updateBountyMessage fails. (Default None)
        :return: The new discord message containing the BBC listing
        :rtype: discord.Message
        :raise ValueError: If guild does not own a bountyBoardChannel
        """
        if not self.hasBountyBoardChannels:
            raise ValueError("The requested BasedGuild has no bountyBoardChannel")
        bountyListing = await bounty.division.bountyBoardChannel.channel.send(msg, embed=embed)
        await bounty.division.bountyBoardChannel.addBounty(bounty, bountyListing)
        await bounty.division.bountyBoardChannel.updateBountyMessage(bounty)
        return bountyListing


    async def removeBountyBoardChannelMessage(self, bounty : bounty.Bounty):
        """Remove guild's bountyBoardChannel listing for bounty.

        :param bounty bounty: The bounty whose BBC listing should be removed
        :raise ValueError: If guild does not own a BBC
        :raise KeyError: If the guild's BBC does not have a listing for bounty
        """
        if not self.hasBountyBoardChannels:
            raise ValueError("The requested BasedGuild has no bountyBoardChannel")
        if bounty.division.bountyBoardChannel.hasMessageForBounty(bounty):
            try:
                await bounty.division.bountyBoardChannel.getMessageForBounty(bounty).delete()
            except HTTPException:
                botState.logger.log("Main", "rmBBCMsg",
                                    "HTTPException thrown when removing bounty listing message for criminal: " \
                                    + bounty.criminal.name, category='bountyBoards', eventType="RM_LISTING-HTTPERR")
            except Forbidden:
                botState.logger.log("Main", "rmBBCMsg",
                                    "Forbidden exception thrown when removing bounty listing message for criminal: " \
                                    + bounty.criminal.name, category='bountyBoards', eventType="RM_LISTING-FORBIDDENERR")
            except NotFound:
                botState.logger.log("Main", "rmBBCMsg",
                                    "Bounty listing message no longer exists, BBC entry removed: " + bounty.criminal.name,
                                    category='bountyBoards', eventType="RM_LISTING-NOT_FOUND")
            await bounty.division.bountyBoardChannel.removeBounty(bounty)
        else:
            raise KeyError("The requested BasedGuild (" + str(self.id) \
                            + ") does not have a bountyBoardChannel listing for the given bounty: " + bounty.criminal.name)


    async def updateBountyBoardChannel(self, bounty : bounty.Bounty, bountyComplete : bool = False):
        """Update the BBC listing for the given bounty in the given server.

        :param bounty bounty: The bounty whose listings should be updated
        :param bool bountyComplete: Whether or not the bounty has now been completed.
                                    When True, bounty listings will be removed rather than updated. (Default False)
        """
        if self.hasBountyBoardChannels:
            if bountyComplete:
                if bounty.division.bountyBoardChannel.hasMessageForBounty(bounty):
                    await self.removeBountyBoardChannelMessage(bounty)
            else:
                if not bounty.division.bountyBoardChannel.hasMessageForBounty(bounty):
                    await self.makeBountyBoardChannelMessage(bounty, "A new bounty is now available from **" \
                                                                    + bounty.faction.title() + "** central command:")
                else:
                    await bounty.division.bountyBoardChannel.updateBountyMessage(bounty)


    async def announceNewBounty(self, newBounty : bounty.Bounty):
        """Announce the creation of a new bounty to this guild's announceChannel, if it has one

        :param bounty newBounty: the bounty to announce
        """
        print("Difficulty", newBounty.techLevel, "New bounty with value:", newBounty.activeShip.getValue())
        # Create the announcement embed
        bountyEmbed = lib.discordUtil.makeEmbed(titleTxt=lib.discordUtil.criminalNameOrDiscrim(newBounty.criminal),
                                                desc=cfg.defaultEmojis.newBounty.sendable + " __New Bounty Available__",
                                                col=bbData.factionColours[newBounty.faction],
                                                thumb=newBounty.criminal.icon, footerTxt=newBounty.faction.title())
        bountyEmbed.add_field(name="**Reward Pool:**", value=str(newBounty.reward) + " Credits")
        bountyEmbed.add_field(name="**Difficulty:**", value=str(newBounty.techLevel))
        bountyEmbed.add_field(name="**See the culprit's loadout with:**",
                                value="`" + self.commandPrefix + "loadout criminal " + newBounty.criminal.name + "`")
        bountyEmbed.add_field(name="**Route:**", value=", ".join(newBounty.route), inline=False)

        # Create the announcement text
        msg = "A new bounty is now available from **" + newBounty.faction.title() + "** central command:"

        if self.hasBountyBoardChannels:
            try:
                if self.hasBountyAlertRoles:
                    msg = f"<@&{newBounty.division.alertRoleID}> {msg}"
                # announce to the given channel
                bountyListing = await newBounty.division.bountyBoardChannel.channel.send(msg, embed=bountyEmbed)
                await newBounty.division.bountyBoardChannel.addBounty(newBounty, bountyListing)
                await newBounty.division.bountyBoardChannel.updateBountyMessage(newBounty)
                return bountyListing

            except Forbidden:
                botState.logger.log("BasedGuild", "anncBnty",
                                    "Failed to post BBCh listing to guild " + botState.client.get_guild(self.id).name + "#" \
                                    + str(self.id) + " in channel " + newBounty.division.bountyBoardChannel.channel.name + "#" \
                                    + str(newBounty.division.bountyBoardChannel.channel.id), category="bountyBoards",
                                    eventType="BBC_NW_FRBDN")

        # If the guild has an announceChannel
        elif self.hasAnnounceChannel():
            # ensure the announceChannel is valid
            currentChannel = self.getAnnounceChannel()
            if currentChannel is not None:
                try:
                    if self.hasBountyAlertRoles:
                        # announce to the given channel
                        await currentChannel.send(f"<@&{newBounty.division.alertRoleID}> {msg}",
                                                    embed=bountyEmbed)
                    else:
                        await currentChannel.send(msg, embed=bountyEmbed)
                except Forbidden:
                    botState.logger.log("BasedGuild", "anncBnty",
                                        "Failed to post announce-channel bounty listing to guild " \
                                        + botState.client.get_guild(self.id).name + "#" + str(self.id) + " in channel " \
                                        + currentChannel.name + "#" + str(currentChannel.id), eventType="ANNCCH_SND_FRBDN")

            # TODO: may wish to add handling for invalid announceChannels - e.g remove them from the BasedGuild object


    async def spawnAndAnnounceBounty(self, newBountyData):
        """Generate a new bounty, either at random or by the given bbBountyConfig, spawn it,
        and announce it if this guild has an appropriate channel selected.
        """
        if self.bountiesDisabled:
            botState.logger.log("basedGuild", "spwnAndAnncBty",
                                "Attempted to spawn a bounty into a guild where bounties are disabled: " \
                                    + (self.dcGuild.name if self.dcGuild is not None else "") + "#" + str(self.id),
                                eventType="BTYS_DISABLED")
            return
        # ensure a new bounty can be created
        if self.bountiesDB.canMakeBounty():
            newBounty: bounty.Bounty = newBountyData["newBounty"]
            config: bountyConfig.BountyConfig = newBountyData["newConfig"].copy() if "newConfig" in newBountyData else bountyConfig.BountyConfig()

            if newBounty is not None:
                div = newBounty.division
                if config.techLevel == -1:
                    config.techLevel = newBounty.techLevel
            elif config.techLevel != -1:
                div = self.bountiesDB.divisionForLevel(config.techLevel)
            else:
                div: "bountyDivision.BountyDivision" = random.choice(list(self.bountiesDB.divisions.values()))
                while div.isFull():
                    div = random.choice(list(self.bountiesDB.divisions.values()))
                config.techLevel = div.pickNewTL()

            if newBounty is None:
                newBounty = bounty.Bounty(division=div, config=config)
            else:
                # If removed, uncomment this line from bounty._respawn
                if self.bountiesDB.escapedCriminalExists(newBounty.criminal):
                    self.bountiesDB.removeEscapedCriminal(newBounty.criminal)

                if config is not None:
                    newConfig = config.copy()
                    if not newConfig.generated:
                        newConfig.generate(div)
                    newBounty.route = newConfig.route
                    newBounty.start = newConfig.start
                    newBounty.end = newConfig.end
                    newBounty.answer = newConfig.answer
                    newBounty.checked = newConfig.checked
                    newBounty.reward = newConfig.reward
                    newBounty.issueTime = newConfig.issueTime
                    newBounty.endTime = newConfig.endTime

            # activate and announce the bounty
            self.bountiesDB.addBounty(newBounty)
            await self.announceNewBounty(newBounty)
        
        else:
            raise OverflowError("Attempted to spawnAndAnnounceBounty when no more space is available for bounties " \
                                + "in the bountiesDB")


    async def announceBountyWon(self, bounty : bounty.Bounty, rewards : Dict[int, Dict[str, Union[int, bool]]],
                                winningUser : Member):
        """Announce the completion of a bounty
        Messages will be sent to the playChannel if one is set

        :param bounty bounty: the bounty to announce
        :param dict rewards: the rewards dictionary as defined by bounty.calculateRewards
        :param discord.Member winningUser: the guild member that won the bounty
        """
        if self.dcGuild is not None:
            if self.hasPlayChannel():
                winningUserId = winningUser.id
                # Create the announcement embed
                rewardsEmbed = lib.discordUtil.makeEmbed(titleTxt="Bounty Complete!",
                                                        authorName=lib.discordUtil.criminalNameOrDiscrim(bounty.criminal) \
                                                        + " Arrested", icon=bounty.criminal.icon,
                                                        col=bbData.factionColours[bounty.faction],
                                                        desc="`Suspect located in '" + bounty.answer + "'`")

                # Add the winning user to the embed
                rewardsEmbed.add_field(name="1. 🏆 " + str(rewards[winningUserId]["reward"]) + " credits:",
                                        value=winningUser.mention + " checked " + str(rewards[winningUserId]["checked"]) \
                                            + " system" + ("s" if int(rewards[winningUserId]["checked"]) != 1 else "") \
                                            + "\n*+" + str(rewards[winningUserId]["xp"]) + "xp*",
                                        inline=False)


                # The index of the current user in the embed
                place = 2
                # Loop over all non-winning users in the rewards dictionary
                for userID in rewards:
                    if not rewards[userID]["won"]:
                        rewardsEmbed.add_field(name=str(place) + ". " + str(rewards[userID]["reward"]) + " credits:",
                                                value="<@" + str(userID) + "> checked " \
                                                    + str(int(rewards[userID]["checked"])) \
                                                    + " system" + ("s" if int(rewards[userID]["checked"]) != 1 else "") \
                                                    + "\n*+" + str(rewards[winningUserId]["xp"]) + "xp*",
                                                inline=False)
                        place += 1

                # Send the announcement to the guild's playChannel
                await self.getPlayChannel().send(":trophy: **You win!**\n**" + winningUser.display_name \
                                                    + "** located and EMP'd **" + bounty.criminal.name \
                                                    + "**, who has been arrested by local security forces. :chains:",
                                                    embed=rewardsEmbed)

        else:
            botState.logger.log("Main", "AnncBtyWn",
                                "None dcGuild received when posting bounty won to guild " \
                                + botState.client.get_guild(self.id).name + "#" + str(self.id) + " in channel ?#" \
                                + str(self.getPlayChannel().id), eventType="DCGUILD_NONE")


    def enableBounties(self):
        """Enable bounties for this guild.
        Sets up a new bounties DB and bounty spawning TimedTask.

        :raise ValueError: If bounties are already enabled in this guild
        """
        if not self.bountiesDisabled:
            raise ValueError("Bounties are already enabled in this guild")

        self.bountiesDB = BountyDB(self)
        self.bountiesDisabled = False


    async def disableBounties(self):
        """Disable bounties for this guild.
        Removes any bountyboard if one is present, and removes the guild's bounties DB and bounty spawning TimedTask.

        :raise ValueError: If bounties are already disabled in this guild
        """
        if self.bountiesDisabled:
            raise ValueError("Bounties are already disabled in this guild")

        if self.hasBountyBoardChannels:
            self.removeBountyBoardChannel()
        self.bountiesDisabled = True
        self.bountiesDB = None

        if self.hasBountyAlertRoles:
            await self.deleteBountyAlertRoles()


    def enableShop(self):
        """Enable the shop for this guild.
        Creates a new guildShop object for this guild.

        :raise ValueError: If the shop is already enabled in this guild
        """
        if not self.shopDisabled:
            raise ValueError("The shop is already enabled in this guild")

        self.shop = guildShop.TechLeveledShop(noRefresh=True)
        self.shopDisabled = False


    def disableShop(self):
        """Disable the shop for this guild.
        Removes the guild's guildShop object.

        :raise ValueError: If the shop is already disabled in this guild
        """
        if self.shopDisabled:
            raise ValueError("The shop is already disabled in this guild")

        self.shop = None
        self.shopDisabled = True


    async def announceNewShopStock(self):
        """Announce to the guild's play channel that this guild's shop stock has been refreshed.
        If no playChannel has been set, does nothing.

        :raise ValueError: If this guild's shop is disabled
        """
        if self.shopDisabled:
            raise ValueError("Attempted to announceNewShopStock on a guild where shop is disabled")
        if self.hasPlayChannel():
            playCh = self.getPlayChannel()
            msg = "The shop stock has been refreshed!\n**        **Now at tech level: **" \
                    + str(self.shop.currentTechLevel) + "**"
            try:
                if self.hasUserAlertRoleID("shop_refresh"):
                    # announce to the given channel
                    await playCh.send(":arrows_counterclockwise: <@&" \
                                        + str(self.getUserAlertRoleID("shop_refresh")) + "> " + msg)
                else:
                    await playCh.send(":arrows_counterclockwise: " + msg)
            except Forbidden:
                botState.logger.log("Main", "anncNwShp",
                                    "Failed to post shop stock announcement to " + self.dcGuild.name + "#" + str(self.id) \
                                    + " in channel " + playCh.name + "#" + str(playCh.id), category="shop",
                                    eventType="PLCH_NONE")


    def toDict(self, **kwargs) -> dict:
        """Serialize this BasedGuild into dictionary format to be saved to file.

        :return: A dictionary containing all information needed to reconstruct this BasedGuild
        :rtype: dict
        """
        data = {    "announceChannel":  self.announceChannel.id if self.hasAnnounceChannel() else -1,
                    "playChannel":      self.playChannel.id if self.hasPlayChannel() else -1,
                    "alertRoles":       self.alertRoles,
                    "ownedRoleMenus":   self.ownedRoleMenus,
                    "bountiesDisabled": self.bountiesDisabled,
                    "shopDisabled":     self.shopDisabled}

        if self.commandPrefix != cfg.defaultCommandPrefix:
            data["commandPrefix"] = self.commandPrefix

        if not self.bountiesDisabled:
            data["bountiesDB"] = self.bountiesDB.toDict(**kwargs)

        if not self.shopDisabled:
            data["shop"] = self.shop.toDict(**kwargs)

        return data


    @classmethod
    def fromDict(cls, guildDict: dict, dbReload=False, **kwargs) -> BasedGuild:
        """Factory function constructing a new BasedGuild object from the information
        in the provided guildDict - the opposite of BasedGuild.toDict

        :param int guildID: The discord ID of the guild
        :param dict guildDict: A dictionary containing all information required to build the BasedGuild object
        :param bool dbReload: Whether or not this guild is being created during the initial database loading phase of
                                bountybot. This is used to toggle name checking in bounty contruction.
        :return: A BasedGuild according to the information in guildDict
        :rtype: BasedGuild
        """
        if "guildID" not in kwargs:
            raise NameError("Required kwarg missing: guildID")
        guildID = kwargs["guildID"]

        dcGuild = botState.client.get_guild(guildID)
        if dcGuild is None:
            raise lib.exceptions.NoneDCGuildObj("Could not get guild object for id " + str(guildID))

        announceChannel = guildDict.get("announceChannel", -1)
        announceChannel = dcGuild.get_channel(announceChannel) if announceChannel != -1 else None
        playChannel = guildDict.get("playChannel", -1)
        playChannel = dcGuild.get_channel(playChannel) if playChannel != -1 else None

        bountiesDisabled = guildDict.get("bountiesDisabled", False)

        if not guildDict.get("shopDisabled", True):
            shop = None
        else:
            if "shop" in guildDict:
                shop = guildShop.TechLeveledShop.fromDict(guildDict["shop"])
            else:
                shop = guildShop.TechLeveledShop()

        newGuild = BasedGuild(**cls._makeDefaults(guildDict, ("bountiesDB","bountyBoardChannel"),
                                                    id=guildID, dcGuild=dcGuild, bounties=None,
                                                    announceChannel=announceChannel, playChannel=playChannel,
                                                    shop=shop, shopDisabled=shop is None))

        if not bountiesDisabled:
            if "bountiesDB" in guildDict:
                bountiesDB = BountyDB.fromDict(guildDict["bountiesDB"], dbReload=dbReload, owningBasedGuild=newGuild)
            else:
                bountiesDB = BountyDB(newGuild)
            newGuild.bountiesDB = bountiesDB
            newGuild.hasBountyBoardChannels = next(i for i in newGuild.bountiesDB.divisions.values()).bountyBoardChannel \
                                                is not None
            newGuild.hasBountyAlertRoles = next(i for i in newGuild.bountiesDB.divisions.values()).alertRoleID != -1

        return newGuild
