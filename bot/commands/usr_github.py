import discord

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import cfg
from ..users import basedGuild, basedUser


botCommands.addHelpSection(0, "github")


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
