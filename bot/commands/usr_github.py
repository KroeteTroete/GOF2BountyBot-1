from typing import Dict, List, Union, cast
import discord

from . import commandsDB as botCommands
from .. import botState, lib
from ..lib.discordUtil import asyncWrap
from ..cfg import cfg
from ..users import basedGuild, basedUser
import difflib

from github import Github
from github.Issue import Issue
from github import UnknownObjectException


botCommands.addHelpSection(0, "github")


@asyncWrap
def searchIssues(searchTerm: str) -> List[Issue]:
    """Search through all pages of the github repository's issues for the top 3 matches for the given search term.
    Searches are performed over issue titles and no other content.
    This is a very expensive operation, use sparingly.

    :param str searchTerm: The issue name to search for
    :return: A list of 0-3 Issues that most closely match search Term
    :rtype: List[Issue]
    """
    currentBest: Dict[str, Issue] = {}
    currentPage = 0

    allIssues = botState.githubRepo.get_issues()
    currentIssues: Dict[str, Issue] = {x.title: x for x in allIssues.get_page(currentPage)}

    while currentIssues:
        currentTerms = set(currentBest.keys())
        currentTerms.update(currentIssues.keys())

        currentBestNames = difflib.get_close_matches(searchTerm, currentTerms, n=3)
        currentBest = {x: currentBest[x] if x in currentBest else currentIssues[x] for x in currentBestNames}

        currentPage += 1
        currentIssues = {x.title: x for x in allIssues.get_page(currentPage)}

    return list(currentBest.values())


@asyncWrap
def getIssueByNumber(issueNumber: int) -> Union[Issue, None]:
    """Get an issue by its number.

    :param int issueNumber: The number of the issue
    :return: The issue with the given number, or None if none exists
    :rtype: Union[Issue, None]
    """
    try:
        return botState.githubRepo.get_issue(issueNumber)
    except UnknownObjectException:
        return None


async def cmd_balance(message : discord.Message, args : str, isDM : bool):
    """print the balance of the specified user, use the calling user if no user is specified.

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention
    :param bool isDM: Whether or not the command is being called from a DM channel
    """


botCommands.register("balance", cmd_balance, 0, aliases=["bal", "credits"], forceKeepArgsCasing=True, allowDM=True,
                        helpSection="economy", signatureStr="**balance** *[user]*",
                        shortHelp="Get the credits balance of yourself, or another user if one is given.",
                        longHelp="Get the credits balance of yourself, or another user if one is given. If used from inside" \
                                    + " of a server, `user` can be a mention, ID, username, or username with discriminator " \
                                    + "(#number). If used from DMs, `user` must be an ID or mention.")
