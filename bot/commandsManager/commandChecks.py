from types import Callable
from typing import Any
import discord
from ..cfg import cfg
from discord.ext.commands import Context

def inferUserPermissions(ctx: Context) -> int:
    """Get the commands access level of the user that sent the given message.

    :return: message.author's access level, as an index of cfg.userAccessLevels
    :rtype: int
    """
    if ctx.author.id in cfg.developers:
        return 3
    elif ctx.author.permissions_in(ctx.channel).administrator:
        return 2
    else:
        return 0

class EnsureAccessLevel(Callable):
    def __init__(self, minLevel: int):
        self.minLevel = minLevel
    
    def __call__(self, ctx: Context) -> bool:
        return inferUserPermissions(ctx) >= self.minLevel