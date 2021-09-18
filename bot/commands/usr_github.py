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


async def cmd_issue_search(message : discord.Message, args : str, isDM : bool):
    """Search for github issues with the given title.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an issue title to search for
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Please give an issue name to search for!")
        return
    
    await lib.discordUtil.startLongProcess(message)
    issues: List[Issue] = await searchIssues(args)

    resultsEmbed = discord.Embed(title="GitHub Issues Search", description=f"Search term: `{args}`\n** **",
                                    colour=discord.colour.Colour.random())
    prefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
    resultsEmbed.set_footer(text=f"GitHub repository linked in `{prefix}source`")
    resultsEmbed.set_thumbnail(url=botState.client.user.avatar_url_as(size=64))
    if issues:
        for issue in issues:
            labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
            resultsEmbed.add_field(name=("🟢" if issue.state == "open" else "🔴") + " " + issue.title,
                                    value=f"[#{issue.number}]({issue.url}) *({labelsStr})*")
    else:
        resultsEmbed.add_field(name="No results found", value="​")

    await message.reply(embed=resultsEmbed)
    await lib.discordUtil.endLongProcess(message)

botCommands.register("issue search", cmd_issue_search, 0, forceKeepArgsCasing=True, allowDM=True,
                        aliases=["bug search", "issues search", "git search", "github search", "feature search"],
                        helpSection="github", signatureStr="**issue search <issue-name>**",
                        shortHelp="Search for GitHub issues with the given name, getting the 3 most similar issues.")


async def cmd_issue(message : discord.Message, args : str, isDM : bool):
    """Various github issues actions

    :param discord.Message message: the discord message calling the command
    :param str args: string containing subcommand name followed by arguments
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    prefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
    if args == "":
        await message.reply(mention_author=False,
                            content=f":x: Please give a subcommand! See `{prefix}help issue` for possible commands.")
        return

    argsSplit = args.split(" ")

    issueCmds = {"search": cmd_issue_search}
    
    if argsSplit[0] in issueCmds:
        await issueCmds[argsSplit[0]](message, args[len(argsSplit[0])+1:], isDM)
    else:
        await message.reply(mention_author=False,
                            content=f":x: Unknown subcommand! See `{prefix}help issue` for possible commands.")

botCommands.register("issue", cmd_issue, 0, allowDM=True, helpSection="github", signatureStr="**issue <subcommand> <args>**",
                        aliases=["git", "github", "bug", "feature", "issues"],
                        shortHelp="Look up and submit new bug reports and feature requests.",
                        longHelp="Look up bugs and feature requests, and submit new ones!\n" \
                            + "To do more with the project's issues, please see the project GitHub repository, " \
                            + "linked in the `source` command.\n\n" \
                            + "subcommands:\n- `search`, to find issues by name")
