from ..users import basedUser
from . import ReactionMenu, expiryFunctions
from discord import Message, Member, Role, Embed
from .. import lib, botState
from typing import Dict
from ..scheduling import TimedTask
from ..cfg import cfg


async def menuJumpToPage(data : dict):
    await botState.reactionMenusDB[data["menuID"]].jumpToPage(data["pageNum"])


class PagedReactionMenu(ReactionMenu.ReactionMenu):
    """A reaction menu that, instead of taking a list of options, takes a list of pages of options.
    """
    saveable = False
    
    def __init__(self, msg : Message, pages : Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.ReactionMenuOption]] = {}, 
                    timeout : TimedTask.TimedTask = None, targetMember : Member = None, targetRole : Role = None, owningBasedUser : basedUser.BasedUser = None,
                    noCancel : bool = False):
        """
        :param discord.Message msg: the message where this menu is embedded
        :param pages: A dictionary associating embeds with pages, where each page is a dictionary storing all options on that page and their behaviour (Default {})
        :type pages: dict[Embed, dict[lib.emojis.BasedEmoji, ReactionMenuOption]]
        :param TimedTask timeout: The TimedTask responsible for expiring this menu (Default None)
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu. All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role. All other reactions are ignored (Default None)
        :param BasedUser owningBasedUser: The user who initiated this menu. No built in behaviour. (Default None)
        """

        self.pages = pages
        self.msg = msg
        self.currentPageNum = 0
        self.currentPage = None
        self.currentPageControls = {}
        self.timeout = timeout
        self.targetMember = targetMember
        self.targetRole = targetRole
        self.owningBasedUser = owningBasedUser

        nextOption = ReactionMenu.NonSaveableReactionMenuOption("Next Page", cfg.defaultNextEmoji, self.nextPage, None)
        prevOption = ReactionMenu.NonSaveableReactionMenuOption("Previous Page", cfg.defaultPreviousEmoji, self.previousPage, None)

        self.firstPageControls = {  cfg.defaultNextEmoji:      nextOption}

        self.midPageControls = {    cfg.defaultNextEmoji:      nextOption,
                                    cfg.defaultPreviousEmoji:  prevOption}

        self.lastPageControls = {   cfg.defaultPreviousEmoji:  prevOption}

        self.onePageControls = {}

        if not noCancel:
            cancelOption = ReactionMenu.NonSaveableReactionMenuOption("Close Menu", cfg.defaultCancelEmoji, self.delete, None)
            for optionsDict in [self.firstPageControls, self.midPageControls, self.lastPageControls, self.onePageControls]:
                optionsDict[cfg.defaultCancelEmoji] = cancelOption

        if len(self.pages) == 1:
            self.currentPageControls = self.onePageControls
        self.updateCurrentPage()


    def getMenuEmbed(self) -> Embed:
        """Generate the discord.Embed representing the reaction menu, and that
        should be embedded into the menu's message.
        This will usually contain a short description of the menu, its options, and its expiry time.

        :return: A discord.Embed representing the menu and its options
        :rtype: discord.Embed 
        """
        return self.currentPage


    def updateCurrentPage(self):
        self.currentPage = list(self.pages.keys())[self.currentPageNum]
        self.options = list(self.pages.values())[self.currentPageNum]

        if len(self.pages) > 1:
            if self.currentPageNum == len(self.pages) - 1:
                self.currentPageControls = self.lastPageControls
            elif self.currentPageNum == 0:
                self.currentPageControls = self.firstPageControls
            else:
                self.currentPageControls = self.midPageControls

        for optionEmoji in self.currentPageControls:
            self.options[optionEmoji] = self.currentPageControls[optionEmoji]


    async def nextPage(self):
        if self.currentPageNum == len(self.pages) - 1:
            raise RuntimeError("Attempted to nextPage while on the last page")
        self.currentPageNum += 1
        self.updateCurrentPage()
        await self.updateMessage(noRefreshOptions=True)
        if self.currentPageNum == len(self.pages) - 1:
            self.msg = await self.msg.channel.fetch_message(self.msg.id)
            await self.msg.remove_reaction(cfg.defaultNextEmoji.sendable, botState.client.user)
        if self.currentPageNum == 1:
            await self.msg.add_reaction(cfg.defaultPreviousEmoji.sendable)


    async def previousPage(self):
        if self.currentPageNum == 0:
            raise RuntimeError("Attempted to previousPage while on the first page")
        self.currentPageNum -= 1
        self.updateCurrentPage()
        await self.updateMessage(noRefreshOptions=True)
        if self.currentPageNum == 0:
            self.msg = await self.msg.channel.fetch_message(self.msg.id)
            await self.msg.remove_reaction(cfg.defaultPreviousEmoji.sendable, botState.client.user)
        if self.currentPageNum == len(self.pages) - 2:
            await self.msg.add_reaction(cfg.defaultNextEmoji.sendable)

    
    async def jumpToPage(self, pageNum : int):
        if pageNum < 0 or pageNum > len(self.pages) - 1:
            raise IndexError("Page number out of range: " + str(pageNum))
        if pageNum != self.currentPageNum:
            self.currentPageNum = pageNum
            self.updateCurrentPage()
            await self.updateMessage(noRefreshOptions=True)
            if len(self.pages) > 1:
                if self.currentPageNum == 0:
                    self.msg = await self.msg.channel.fetch_message(self.msg.id)
                    await self.msg.remove_reaction(cfg.defaultPreviousEmoji.sendable, botState.client.user)
                if self.currentPageNum != len(self.pages) - 1:
                    await self.msg.add_reaction(cfg.defaultNextEmoji.sendable)


class MultiPageOptionPicker(PagedReactionMenu):
    def __init__(self, msg : Message, pages : Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.NonSaveableSelecterMenuOption]] = {}, 
                    timeout : TimedTask.TimedTask = None, targetMember : Member = None, targetRole : Role = None, owningBasedUser : basedUser.BasedUser = None):
        
        self.selectedOptions = {}
        for pageOptions in pages.values():
            for option in pageOptions.values():
                self.selectedOptions[option] = False

        for pageEmbed in pages:
            if cfg.defaultAcceptEmoji not in pages[pageEmbed]:
                pages[pageEmbed][cfg.defaultAcceptEmoji] = ReactionMenu.NonSaveableReactionMenuOption("Submit", cfg.defaultAcceptEmoji, self.delete, None)

            if cfg.defaultCancelEmoji not in pages[pageEmbed]:
                pages[pageEmbed][cfg.defaultCancelEmoji] = ReactionMenu.NonSaveableReactionMenuOption("Cancel Game", cfg.defaultCancelEmoji, expiryFunctions.deleteReactionMenu, msg.id)

            if cfg.spiralEmoji not in pages[pageEmbed]:
                pages[pageEmbed][cfg.spiralEmoji] = ReactionMenu.NonSaveableReactionMenuOption("Toggle All", cfg.spiralEmoji,
                                                                                                addFunc=ReactionMenu.selectorSelectAllOptions, addArgs=msg.id,
                                                                                                removeFunc=ReactionMenu.selectorDeselectAllOptions, removeArgs=msg.id)

        super().__init__(msg, pages=pages, timeout=timeout, targetMember=targetMember, targetRole=targetRole, owningBasedUser=owningBasedUser, noCancel=True)


    async def updateSelectionsField(self):
        newSelectedStr = ", ".join(option.name for option in self.selectedOptions if self.selectedOptions[option])
        newSelectedStr = newSelectedStr if newSelectedStr else "​"

        for pageEmbed in self.pages:
            for fieldIndex in range(len(pageEmbed.fields)):
                field = pageEmbed.fields[fieldIndex]
                if field.name == "Currently selected:":
                    pageEmbed.set_field_at(fieldIndex, name=field.name, value=newSelectedStr)
                break

        await self.updateMessage(noRefreshOptions=True)