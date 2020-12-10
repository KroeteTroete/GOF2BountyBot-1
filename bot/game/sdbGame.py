from urllib import request
import json
from .. import botState
from typing import Dict, Union

class SDBGame:
    def __init__(self, owner, meta_url, expansionNames):
        self.owner = owner
        self.meta_url = meta_url
        deckMeta = json.load(request.urlopen(meta_url))
        self.expansionNames = expansionNames
        self.deckName = deckMeta["deck_name"]
        self.expansions = {}
        for expansionName in expansionNames:
            self.expansions[expansionName] = deckMeta["expansions"][expansionName]


async def startGameFromExpansionMenu(gameCfg : Dict[str, Union[str, int]]):
    menu = botState.reactionMenusDB[gameCfg["menuID"]]
    callingBGuild = botState.guildsDB.getGuild(menu.msg.guild.id)

    expansionNames = []
    for option in menu.selectedOptions:
        if menu.selectedOptions[option]:
            expansionNames.append(option.name)

    await callingBGuild.startGame(menu.msg.author, menu.msg.channel, gameCfg["deckName"], expansionNames)