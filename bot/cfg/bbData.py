from discord import Colour
# Used for importing items
import os
import json
from . import cfg

CWD = os.getcwd()


def loadGameItemsFromDir(itemDir, itemFolderExt):
    itemDB = {}
    itemFolderExt = itemFolderExt.lower()
    for subdir, dirs, _ in os.walk(itemDir):
        for dirname in dirs:
            dirpath = subdir + os.sep + dirname

            if dirname.lower().endswith(itemFolderExt):
                with open(dirpath + os.sep + "META.json", "r") as f:
                    currentItemData = json.loads(f.read())
                    itemDB[currentItemData["name"]] = currentItemData
    print("[bbData] " + str(len(itemDB)) + " " + itemFolderExt + "s loaded.")
    return itemDB


def loadbbShipsFromDir(shipsDir):
    itemDB = {}
    for subdir, dirs, _ in os.walk(shipsDir):
        for dirname in dirs:
            dirpath = subdir + os.sep + dirname

            if dirname.lower().endswith(".bbship"):
                with open(dirpath + os.sep + "META.json", "r") as f:
                    currentItemData = json.loads(f.read())
                    currentItemData["path"] = CWD + os.sep + dirpath
                    if "skinnable" not in currentItemData or "model" not in currentItemData:
                        currentItemData["skinnable"] = False
                    itemDB[currentItemData["name"]] = currentItemData

                    if "compatibleSkins" not in currentItemData:
                        currentItemData["compatibleSkins"] = []
    print("[bbData] " + str(len(itemDB)) + " .bbShips loaded.")
    return itemDB


# all factions recognised by BB
factions = ["terran", "vossk", "midorian", "nivelian", "neutral"]
# all factions useable in bounties
bountyFactions = ["terran", "vossk", "midorian", "nivelian"]

# levels of security in bbSystems (bbSystem security is stored as an index in this list)
securityLevels = ["secure", "average", "risky", "dangerous"]

# map image URLS for cmd_map
mapImageWithGraphLink = "https://cdn.discordapp.com/attachments/700683544103747594/700683693215318076/gof2_coords.png"
mapImageNoGraphLink = 'https://i.imgur.com/TmPgPd3.png'

# icons for factions
factionIcons = {"terran": "https://cdn.discordapp.com/attachments/700683544103747594/711013574331596850/terran.png",
                "vossk": "https://cdn.discordapp.com/attachments/700683544103747594/711013681621893130/vossk.png",
                "midorian": "https://cdn.discordapp.com/attachments/700683544103747594/711013601019691038/midorian.png",
                "nivelian": "https://cdn.discordapp.com/attachments/700683544103747594/711013623257890857/nivelian.png",
                "neutral":
                    "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/rocket_1f680.png",
                "void": "https://cdn.discordapp.com/attachments/700683544103747594/711013699841687602/void.png"}

errorIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/exclamation-mark_2757.png"
winIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/trophy_1f3c6.png"
rocketIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/rocket_1f680.png"

# colours to use in faction-related embed strips
factionColours = {  "terran":Colour.gold(),
                    "vossk":Colour.dark_green(),
                    "midorian":Colour.dark_red(),
                    "nivelian":Colour.dark_blue(),
                    "neutral":Colour.purple()}

# Data representing all ship items in the game. These are used to create bbShip objects,
# which are stored in builtInShipObjs in a similar dict format.
# Ships to not have tech levels in GOF2, so tech levels will be automaticaly generated
# for the sake of the bot during bot.on_ready.
builtInShipData = loadbbShipsFromDir(cfg.paths.bbShipMETAFolder)

# Data representing all module items in the game. These are used to create bbModule objects,
# which are stored in builtInModuleObjs in a similar dict format.
builtInModuleData = loadGameItemsFromDir(cfg.paths.bbModuleMETAFolder, ".bbModule")

# Data representing all primary weapon items in the game. These are used to create bbWeapon objects,
# which are stored in builtInWeaponObjs in a similar dict format.
builtInWeaponData = loadGameItemsFromDir(cfg.paths.bbWeaponMETAFolder, ".bbWeapon")

# Data representing all ship upgrades in the game. These are used to create bbShipUpgrade objects,
# which are stored in builtInUpgradeObjs in a similar dict format.
builtInUpgradeData = loadGameItemsFromDir(cfg.paths.bbShipUpgradesMETAFolder, ".bbShipUpgrade")

# data for builtIn criminals to be used in bbCriminal.fromDict
# criminals marked as not builtIn to allow for dictionary init.
# The criminal object is then marked as builtIn during bot.on_ready
builtInCriminalData = loadGameItemsFromDir(cfg.paths.bbCriminalMETAFolder, ".bbCriminal")

# names of criminals in builtIn bounties
bountyNames = {}
# the length of the longest criminal name, to be used in padding during cmd_bounties
longestBountyNameLength = 0

# Fetch bounty names and longest bounty name
for criminalName in builtInCriminalData:
    if builtInCriminalData[criminalName]["faction"] not in bountyNames:
        bountyNames[builtInCriminalData[criminalName]["faction"]] = []
    bountyNames[builtInCriminalData[criminalName]["faction"]].append(criminalName)
    if len(criminalName) > longestBountyNameLength:
        longestBountyNameLength = len(criminalName)

# data for builtIn systems to be used in bbSystem.fromDict
builtInSystemData = loadGameItemsFromDir(cfg.paths.bbSystemMETAFolder, ".bbSystem")

# data for builtIn Turrets to be used in bbTurret.fromDict
builtInTurretData = loadGameItemsFromDir(cfg.paths.bbTurretMETAFolder, ".bbTurret")

# data for builtIn commodities to be used in bbCommodity.fromDict (unimplemented)
builtInCommodityData = loadGameItemsFromDir(cfg.paths.bbCommodityMETAFolder, ".bbCommodity")

builtInToolData = {}

# data for builtIn secondaries to be used in bbSecondary.fromDict (unimplemented)
builtInSecondariesData = loadGameItemsFromDir(cfg.paths.bbModuleMETAFolder, ".bbModule")


# Objects representing all ship skins in the game.
builtInShipSkins = {}
builtInToolObjs = {}
# To be populated during bot.on_ready
# These dicts contain item name: item object for the object described in the variable name.
# This is primarily for use in their relevent fromDict functions.
builtInSystemObjs = {}
builtInCriminalObjs = {}
# Ships are now stored as keys (names) rather than objects, as ships are no longer shared - every user has a unique ship object to allow for customisation
# builtInShipObjs = {}
builtInModuleObjs = {}
builtInWeaponObjs = {}
builtInUpgradeObjs = {}
builtInTurretObjs = {}

# References to the above item objects, sorted by techLevel.
shipKeysByTL = []
moduleObjsByTL = []
weaponObjsByTL = []
turretObjsByTL = []