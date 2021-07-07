import os
import json
from typing import Dict, Any, List
from types import FunctionType

from . import cfg, bbData
from ..gameObjects import shipUpgrade, shipSkin
from ..gameObjects.bounties import criminal, solarSystem
from ..gameObjects.items import moduleItemFactory
from ..gameObjects.items.weapons import primaryWeapon, turretWeapon
from ..gameObjects.items.tools import shipSkinTool, toolItemFactory, crateTool
from ..gameObjects.userProfile import medal
from .. import lib
from ..lib import gameMaths

CWD = os.getcwd()


def _loadGameItemsFromDir(itemDir : str, itemFolderExt : str, lowerKey: bool = False) -> Dict[str, dict]:
    """Load metadata for all configured metadata of one game object type into a new dictionary.

    :param str itemDir: The directory in which to search for items of the given type
    :param str itemFolderExt: The folder extension by which to identify items of the desired type
    :return: A dictionary associating game object names with the metadata found for that object
    :rtype: Dict[str, Dict]
    """
    itemDB = {}
    rawFolderExt = itemFolderExt.lstrip(".")
    itemFolderExt = itemFolderExt.lower()
    # Scan all subdirectories recursively, looking for folders ending with the given extension
    for subdir, dirs, _ in lib.jsonHandler.depthLimitedWalk(itemDir, cfg.gameObjectCfgMaxRecursion):
        for dirname in dirs:
            if dirname.lower().endswith(itemFolderExt):
                dirpath = subdir + os.sep + dirname
                # Ensure a meta file exists
                if not os.path.isfile(dirpath + os.sep + "META.json"):
                    raise lib.exceptions.InvalidGameObjectFolder(dirpath, "missing META.json")

                # Read in the object metadata and add to the database
                with open(dirpath + os.sep + "META.json", "r") as f:
                    currentItemData = json.loads(f.read())
                    if lowerKey:
                        itemDB[currentItemData["name"].lower()] = currentItemData
                    else:
                        itemDB[currentItemData["name"]] = currentItemData
    print("[gameConfigurator] " + str(len(itemDB)) + " " + rawFolderExt + "s loaded.")
    return itemDB


def _loadShipItemsFromDir(shipsDir : str) -> Dict[str, dict]:
    """Load metadata for all configured Ship metadata into a new dictionary.
    This function also assigns an autogenerated tech level to the ship meta, based on its value attribute.

    :param str shipsDir: The directory in which to search for Ship item configuration folders
    :return: A dictionary associating ship names with the metadata found for that ship
    :rtype: Dict[str, Dict]
    """
    itemDB = {}
    # Scan all subdirectories recursively, looking for folders ending with .bbShip
    for subdir, dirs, _ in lib.jsonHandler.depthLimitedWalk(shipsDir, cfg.gameObjectCfgMaxRecursion):
        for dirname in dirs:
            if dirname.lower().endswith(".bbship"):
                dirpath = subdir + os.sep + dirname

                # Ensure a meta file exists
                if not os.path.isfile(dirpath + os.sep + "META.json"):
                    raise lib.exceptions.InvalidGameObjectFolder(dirpath, "missing META.json")

                # Read in the ship metadata
                with open(dirpath + os.sep + "META.json", "r") as f:
                    currentItemData = json.loads(f.read())

                # Set the ship config file path, for use later when locating model files
                currentItemData["path"] = CWD + os.sep + dirpath

                # Default skinnable attribute to False
                if "skinnable" not in currentItemData or "model" not in currentItemData:
                    currentItemData["skinnable"] = False

                # Default compatibleSkins attribute to no skins
                if "compatibleSkins" not in currentItemData:
                    currentItemData["compatibleSkins"] = []

                # Generate tech level based on ship value
                if "value" not in currentItemData:
                    print("[gameConfigurator] No value found for ShipItem. Assigning techlevel of -1: " + dirpath)
                    currentItemData["techLevel"] = -1
                else:
                    for tl in range(len(cfg.shipMaxPriceTechLevels)):
                        if cfg.shipMaxPriceTechLevels[tl] >= currentItemData["value"]:
                            currentItemData["techLevel"] = tl + 1
                            break

                # add to the database
                itemDB[currentItemData["name"]] = currentItemData
    print("[gameConfigurator] " + str(len(itemDB)) + " Ships loaded.")
    return itemDB


def _loadShipSkinsFromDir(shipsDir : str) -> Dict[str, dict]:
    """Load metadata for all configured ShipSkin metadata into a new dictionary.

    :param str shipSkinsDir: The directory in which to search for ShipSkin item configuration folders
    :return: A dictionary associating skin names with the metadata found for that skin
    :rtype: Dict[str, Dict]
    """
    itemDB = {}
    # Scan all subdirectories recursively, looking for folders ending with .bbShip
    for subdir, dirs, _ in lib.jsonHandler.depthLimitedWalk(shipsDir, cfg.gameObjectCfgMaxRecursion):
        for dirname in dirs:
            if dirname.lower().endswith(".bbshipskin"):
                dirpath = subdir + os.sep + dirname

                # Ensure a meta file exists
                if not os.path.isfile(dirpath + os.sep + "META.json"):
                    raise lib.exceptions.InvalidGameObjectFolder(dirpath, "missing META.json")

                # Read in the skin metadata
                with open(dirpath + os.sep + "META.json", "r") as f:
                    currentItemData = json.loads(f.read())

                currentItemData["path"] = CWD + os.sep + dirpath

                # register the skin to the database under the LOWER-shifted skin name
                itemDB[currentItemData["name"].lower()] = currentItemData
    print("[gameConfigurator] " + str(len(itemDB)) + " ShipSkins loaded.")
    return itemDB


def _loadGameObjects(dataDB : Dict[str, dict], objsDB : Dict[str, Any], deserializer: FunctionType):
    """Spawn in builtIn instances of all objects described in dataDB, and register into objsDB.
    Objects are created with the given deserializer as a constructor.
    Objects are registered directly into objsDB, and the metadata in dataDB is updated to be builtIn.
    No new dictionaries are created.
    """
    for objKey, objDict in dataDB.items():
        objsDB[objKey] = deserializer(objDict)
        objsDB[objKey].builtIn = True
        dataDB[objKey]["builtIn"] = True


def _loadToolObjects(dataDB : Dict[str, dict], objsDB : Dict[str, Any], deserializer: FunctionType):
    """Spawn in builtIn instances of all ToolItems described in dataDB, and register into objsDB.
    This is the same as _loadGameObjects, with the extra step of checking all spawned tools to see if they are crates,
    and adding crates to bbData.builtInCrateObjs.
    """
    for objDict in dataDB.values():
        newTool = deserializer(objDict)
        newTool.builtIn = True
        objsDB[newTool.name] = newTool
        dataDB[newTool.name]["builtIn"] = True
        if isinstance(newTool, crateTool.CrateTool):
            if newTool.crateType not in bbData.builtInCrateObjs:
                raise ValueError("Unknown cratetype for crate '" + newTool.name + "': " + newTool.crateType)
            if len(bbData.builtInCrateObjs[newTool.crateType]) < newTool.typeNum + 1:
                slotsToAdd = newTool.typeNum - len(bbData.builtInCrateObjs[newTool.crateType]) + 1
                bbData.builtInCrateObjs[newTool.crateType] += [None] * slotsToAdd
            bbData.builtInCrateObjs[newTool.crateType][newTool.typeNum] = newTool


def _sortShipKeys():
    """Populate bbData.shipKeysByTL with the names of ships from bbData.builtInShipData, sorted by tech level.
    """
    # Initialise shipKeysByTL as maxTechLevel empty arrays
    bbData.shipKeysByTL = [[] for _ in range(cfg.minTechLevel, cfg.maxTechLevel + 1)]

    # Sort ship keys by tech level
    for currentShipKey in bbData.builtInShipData.keys():
        if bbData.builtInShipData[currentShipKey]["techLevel"] == -1:
            print("[gameConfig] techLevel -1 found for ShipItem. Excluding this Ship from bbData.shipKeysByTL: " \
                    + currentShipKey)
        else:
            bbData.shipKeysByTL[bbData.builtInShipData[currentShipKey]["techLevel"] - 1].append(currentShipKey)


def _sortGameObjects(objsDB : Dict[str, Any]) -> List[List[Any]]:
    """Create a list, containing lists the objects found in objsDB, sorted by tech level.

    :return: A list with one sub-list for each techlevel, each containing the items in objsDB of that tech Level.
    :rtype: List[List[Any]]
    """
    # Sort module objects by tech level
    sortedDB = [[] for _ in range(cfg.maxTechLevel - cfg.minTechLevel + 1)]
    for obj in objsDB.values():
        sortedDB[obj.techLevel - 1].append(obj)
    return sortedDB


def _makeShipSpawnRates():
    """Calculate spawn rates for the ship metadatas found in bbData.builtInShipData, based on their techLevels.
    """
    for ship in bbData.builtInShipData.values():
        unnormalizedChance = gameMaths.itemTLSpawnChanceForShopTL[ship["techLevel"] - 1][ship["techLevel"] - 1]
        normalizedChance = unnormalizedChance / len(bbData.shipKeysByTL[ship["techLevel"] - 1])
        ship["shopSpawnRate"] = gameMaths.truncItemSpawnResolution(normalizedChance * 100)


def _makeItemSpawnRates(objsDB : Dict[str, Any]):
    """Calculate spawn rates for the game object instances found in objsDB, based on their techLevels.
    Spawn rates are then stored in the items' shopSpawnRate attributes.
    """
    for item in objsDB.values():
        unnormalizedChance = gameMaths.itemTLSpawnChanceForShopTL[item.techLevel - 1][item.techLevel - 1]
        normalizedChance = unnormalizedChance / len(bbData.shipKeysByTL[item.techLevel - 1])
        item.shopSpawnRate = gameMaths.truncItemSpawnResolution(normalizedChance * 100)


def _makeLevelUpCrates():
    crates = [crateTool.CrateTool([], "$INVALID_CRATE_LUP0$", [], builtIn=True)] + [None] * gameMaths.numTechLevels

    # generate bbCrates for bbShipSkinTools for each player bounty hunter level up
    for level in gameMaths.techLevelRange:
        itemPool = []
        shipSkins = set()
        for shipName in bbData.shipKeysByTL[level-1]:
            if "compatibleSkins" in bbData.builtInShipData[shipName]:
                for skinName in bbData.builtInShipData[shipName]["compatibleSkins"]:
                    if bbData.builtInShipSkins[skinName] not in shipSkins:
                        shipSkins.add(bbData.builtInShipSkins[skinName])

        itemPool = [bbData.shipSkinToolsBySkin[skin] for skin in shipSkins]
        crates[level] = crateTool.CrateTool(itemPool, "Level " + str(level) + " skins crate", techLevel=level,
                                                builtIn=True, value=gameMaths.crateValueForTL(level),
                                                crateType="levelUp", typeNum=level)
    return crates


def loadAllGameObjectData():
    """Load json descriptions of all configured game objects into bbData variables.
    This function populates:

    bbData.builtInShipData
    bbData.builtInModuleData
    bbData.builtInWeaponData
    bbData.builtInUpgradeData
    bbData.builtInCriminalData
    bbData.builtInSystemData
    bbData.builtInTurretData
    bbData.builtInCommodityData
    bbData.builtInToolData
    bbData.builtInSecondariesData
    bbData.builtInShipSkinsData
    bbData.medalsData
    """
    bbData.builtInShipData = _loadShipItemsFromDir(cfg.paths.bbShipMETAFolder)
    bbData.builtInShipSkinsData = _loadShipSkinsFromDir(cfg.paths.shipSkinMETAFolder)

    for db, dir, ext in (   ("builtInModuleData",     cfg.paths.bbModuleMETAFolder,       ".bbModule"),
                            ("builtInWeaponData",     cfg.paths.bbWeaponMETAFolder,       ".bbWeapon"),
                            ("builtInUpgradeData",    cfg.paths.bbShipUpgradesMETAFolder, ".bbShipUpgrade"),
                            ("builtInCriminalData",   cfg.paths.CriminalMETAFolder,       ".bbCriminal"),
                            ("builtInSystemData",     cfg.paths.SolarSystemMETAFolder,    ".bbSystem"),
                            ("builtInTurretData",     cfg.paths.bbTurretMETAFolder,       ".bbTurret"),
                            ("builtInCommodityData",  cfg.paths.bbCommodityMETAFolder,    ".bbCommodity"),
                            ("builtInToolData",       cfg.paths.bbToolMETAFolder,         ".bbTool"),
                            ("builtInSecondariesData",cfg.paths.bbModuleMETAFolder,       ".bbModule"),
                            ("medalsData",            cfg.paths.bbMedalsMETAFolder,       ".bbMedal")):
        setattr(bbData, db, _loadGameItemsFromDir(dir, ext, lowerKey=ext==".bbMedal"))


def loadAllGameObjects():
    """Instance all objects described by the metadata found in bbData, and store those instances in bbData variables.
    ShipSkinTools are created for all ShipSkins for which there is no existing tool in builtInToolData.
    Shop spawn rates are then calculated for each instanced game object.
    Finally, sorted references to these objects are placed into bbData variables.

    This function populates:

    bbData.builtInModuleObjs
    bbData.builtInWeaponObjs
    bbData.builtInUpgradeObjs
    bbData.builtInCriminalObjs
    bbData.builtInSystemObjs
    bbData.builtInTurretObjs
    bbData.builtInToolObjs
    bbData.builtInShipSkins
    bbData.medalObjs

    bbData.shipKeysByTL
    bbData.moduleObjsByTL
    bbData.weaponObjsByTL
    bbData.turretObjsByTL

    This function currently does NOT populate:
    bbData.builtInCommodityObjs
    bbData.builtInSecondariesObjs
    """
    for dataDB, objsDB, deserializer in (
                (bbData.builtInCriminalData,bbData.builtInCriminalObjs, criminal.Criminal.fromDict),
                (bbData.builtInSystemData,  bbData.builtInSystemObjs,   solarSystem.SolarSystem.fromDict),
                (bbData.builtInWeaponData,  bbData.builtInWeaponObjs,   primaryWeapon.PrimaryWeapon.fromDict),
                (bbData.builtInUpgradeData, bbData.builtInUpgradeObjs,  shipUpgrade.ShipUpgrade.fromDict),
                (bbData.builtInTurretData,  bbData.builtInTurretObjs,   turretWeapon.TurretWeapon.fromDict),
                (bbData.builtInModuleData,  bbData.builtInModuleObjs,   moduleItemFactory.fromDict),
                (bbData.builtInShipSkinsData,bbData.builtInShipSkins,   shipSkin.ShipSkin.fromDict),
                (bbData.medalsData,         bbData.medalObjs,           medal.Medal.fromDict)):
        _loadGameObjects(dataDB, objsDB, deserializer)

    # generate shipSkinTool objects for each shipSkin
    for currentSkin in bbData.builtInShipSkins.values():
        # if len(currentSkin.compatibleShips) > 0:
        toolName = lib.stringTyping.shipSkinNameToToolName(currentSkin.name)
        if toolName not in bbData.builtInToolObjs:
            newTool = shipSkinTool.ShipSkinTool(currentSkin, value=gameMaths.shipSkinValueForTL(currentSkin.averageTL),
                                                builtIn=True)
            bbData.builtInToolObjs[toolName] = newTool

        # Register skin tools in shipSkinToolsBySkin
        if currentSkin not in bbData.shipSkinToolsBySkin:
            bbData.shipSkinToolsBySkin[currentSkin] = bbData.builtInToolObjs[toolName]

    _sortShipKeys()
    _makeShipSpawnRates()

    for db, objsDB in ( ("moduleObjsByTL", bbData.builtInModuleObjs),
                        ("weaponObjsByTL", bbData.builtInWeaponObjs),
                        ("turretObjsByTL", bbData.builtInTurretObjs)):
        setattr(bbData, db, _sortGameObjects(objsDB))
        _makeItemSpawnRates(objsDB)

    bbData.builtInCrateObjs = {crateType: [] for crateType in cfg.crateTypes}
    # Load in tools
    _loadToolObjects(bbData.builtInToolData, bbData.builtInToolObjs, toolItemFactory.fromDict)

    bbData.builtInCrateObjs["levelUp"] = _makeLevelUpCrates()

    # Fetch bounty names and longest bounty name
    for criminalName in bbData.builtInCriminalData:
        if bbData.builtInCriminalData[criminalName]["faction"] not in bbData.bountyNames:
            bbData.bountyNames[bbData.builtInCriminalData[criminalName]["faction"]] = []
        bbData.bountyNames[bbData.builtInCriminalData[criminalName]["faction"]].append(criminalName)
        if len(criminalName) > bbData.longestBountyNameLength:
            bbData.longestBountyNameLength = len(criminalName)
