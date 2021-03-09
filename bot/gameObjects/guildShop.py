# Typing imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..users import basedUser

from ..cfg import bbData, cfg
from .items import moduleItemFactory, shipItem, gameItem
from .items.weapons import primaryWeapon, turretWeapon
from .items.modules import moduleItem
from .items.tools import toolItem, toolItemFactory
from .inventories import inventory
import random
from .. import botState
from ..lib import gameMaths
from ..baseClasses import serializable


class GuildShop(serializable.Serializable):
    """A shop containing a selection of items which players can buy.
    Items can be sold to the shop to the shop's inventory and listed for sale.

    :var shipsStock: A inventory containing the shop's stock of ships
    :vartype shipsStock: inventory
    :var weaponsStock: A inventory containing the shop's stock of weapons
    :vartype weaponsStock: inventory
    :var modulesStock: A inventory containing the shop's stock of modules
    :vartype modulesStock: inventory
    :var turretsStock: A inventory containing the shop's stock of turrets
    :vartype turretsStock: inventory
    :var toolsStock: A bbInventory containing the shop's stock of tools
    :vartype toolsStock: bbInventory
    """

    def __init__(self, shipsStock : inventory.Inventory = inventory.TypeRestrictedInventory(shipItem.Ship),
            weaponsStock : inventory.Inventory = inventory.TypeRestrictedInventory(primaryWeapon.PrimaryWeapon),
            modulesStock : inventory.Inventory = inventory.TypeRestrictedInventory(moduleItem.ModuleItem),
            turretsStock : inventory.Inventory = inventory.TypeRestrictedInventory(turretWeapon.TurretWeapon),
            toolsStock : inventory.Inventory = inventory.TypeRestrictedInventory(toolItem.ToolItem)):
        """
        :param inventory shipsStock: The shop's current stock of ships (Default empty inventory)
        :param inventory weaponsStock: The shop's current stock of weapons (Default empty inventory)
        :param inventory modulesStock: The shop's current stock of modules (Default empty inventory)
        :param inventory turretsStock: The shop's current stock of turrets (Default empty inventory)
        :param inventory toolsStock: The shop's current stock of tools (Default empty inventory)
        """

        # TODO: Somewhere, stocks are getting passed in and shared amongst all shops. Fix this. Temporary inventory clear here
        #       to make sure each shop gets its own inventory objects.
        self.shipsStock: inventory.Inventory = inventory.TypeRestrictedInventory(shipItem.Ship)
        self.weaponsStock: inventory.Inventory = inventory.TypeRestrictedInventory(primaryWeapon.PrimaryWeapon)
        self.modulesStock: inventory.Inventory = inventory.TypeRestrictedInventory(moduleItem.ModuleItem)
        self.turretsStock: inventory.Inventory = inventory.TypeRestrictedInventory(turretWeapon.TurretWeapon)
        self.toolsStock: inventory.Inventory = inventory.TypeRestrictedInventory(toolItem.ToolItem)

        for inInv, outInv in [(shipsStock, self.shipsStock),
                        (weaponsStock, self.weaponsStock),
                        (modulesStock, self.modulesStock),
                        (turretsStock, self.turretsStock),
                        (toolsStock, self.toolsStock)]:
            for itemListing in inInv.items.values():
                outInv.addItem(itemListing.item, itemListing.count)


    def getStockByName(self, item : str) -> inventory.Inventory:
        """Get the inventory containing all current stock of the named type.
        This object is mutable and can alter the stock of the shop.

        :param str item: The name of the item type to fetch. Must be one of ship, weapon, module or turret
        :return: The inventory used by the shop to store all stock of the requested type
        :rtype: inventory
        :raise ValueError: When requesting an unknown item type
        :raise NotImplementedError: When requesting a valid item type, but one that is not implemented yet (e.g commodity)
        """
        if item == "all" or item not in cfg.validItemNames:
            raise ValueError("Invalid item type: " + item)
        if item == "ship":
            return self.shipsStock
        if item == "weapon":
            return self.weaponsStock
        if item == "module":
            return self.modulesStock
        if item == "turret":
            return self.turretsStock
        if item == "tool":
            return self.toolsStock
        else:
            raise NotImplementedError("Valid, but unrecognised item type: " + item)


    def userCanAffordItemObj(self, user : basedUser.BasedUser, item : gameItem.GameItem) -> bool:
        """Decide whether a user has enough credits to buy an item

        :param basedUser user: The user whose credits balance to check
        :param gameItem item: The item whose value to check
        :return: True if user's credits balance is greater than or equal to item's value. False otherwise
        :rtype: bool
        """
        return user.credits >= item.getValue()


    ##### SHIP MANAGEMENT #####


    def userCanAffordShipIndex(self, user : basedUser.BasedUser, index : int) -> bool:
        """Decide whether a user can afford to buy a ship from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the ship whose value to check, in the shop's ship inventory's array of keys
        :return: True if user can afford to buy ship number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.shipsStock[index].item)


    def amountCanAffordShipObj(self, amount : int, ship : shipItem.Ship) -> bool:
        """Decide whether amount of credits is enough to buy a ship from the shop's stock.
        This is used for checking whether a user would be able to afford a ship, if they sold their active one.

        :param int amount: The amount of credits to check against the ship's value
        :param shipItem ship: ship object whose value to check against credits
        :return: True if amount is at least as much as ship's value, false otherwise
        :rtype: bool
        """
        return amount >= ship.getValue()


    def amountCanAffordShipIndex(self, amount : int, index : int) -> bool:
        """Decide whether amount of credits is enough to buy the ship at the given index in the shop's stock.
        This is used for checking whether a user would be able to afford a ship, if they sold their active one.

        :param int amount: The amount of credits to check against the ship's value
        :param int index: The index of the ship whose value to check, in the shop's ship inventory's array of keys
        :return: True if amount is at least as much as the ship's value, false otherwise
        :rtype: bool
        """
        return self.amountCanAffordShipObj(amount, self.shipsStock[index].item)


    def userBuyShipIndex(self, user : basedUser.BasedUser, index : int):
        """Sell the ship at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the ship
        :param int index: The index of the requested ship in the shop's ships inventory's array of keys
        """
        self.userBuyShipObj(user, self.shipsStock[index].item)


    def userBuyShipObj(self, user : basedUser.BasedUser, requestedShip : shipItem.Ship):
        """Sell the given ship to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the ship
        :param shipItem requestedWeapon: The ship to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedWeapon
        """
        if self.userCanAffordItemObj(user, requestedShip):
            self.shipsStock.removeItem(requestedShip)
            user.credits -= requestedShip.getValue()
            user.inactiveShips.addItem(requestedShip)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy ship " + requestedShip.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedShip.getValue()))


    def userSellShipObj(self, user : basedUser.BasedUser, ship : shipItem.Ship):
        """Buy the given ship from the given user,
        adding the appropriate credits to their balance and adding the ship to the shop stock.

        :param basedUser user: The user to buy ship from
        :param shipItem weapon: The ship to buy from user
        """
        user.credits += ship.getValue()
        self.shipsStock.addItem(ship)
        user.inactiveShips.removeItem(ship)


    def userSellShipIndex(self, user : basedUser.BasedUser, index : int):
        """Buy the weapon at the given index in the given user's ships inventory,
        adding the appropriate credits to their balance and adding the ship to the shop stock.

        :param basedUser user: The user to buy ship from
        :param int index: The index of the weapon to buy from user, in the user's ships inventory's array of keys
        """
        self.userSellShipObj(user, user.inactiveShips[index].item)


    ##### WEAPON MANAGEMENT #####


    def userCanAffordWeaponIndex(self, user : basedUser.BasedUser, index : int) -> bool:
        """Decide whether a user can afford to buy a weapon from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the weapon whose value to check, in the shop's weapon inventory's array of keys
        :return: True if user can afford to buy weapon number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.weaponsStock[index].item)


    def userBuyWeaponIndex(self, user : basedUser.BasedUser, index : int):
        """Sell the weapon at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the weapon
        :param int index: The index of the requested weapon in the shop's weapons inventory's array of keys
        """
        self.userBuyWeaponObj(user, self.weaponsStock[index].item)


    def userBuyWeaponObj(self, user : basedUser.BasedUser, requestedWeapon : primaryWeapon.PrimaryWeapon):
        """Sell the given weapon to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the weapon
        :param primaryWeapon requestedWeapon: The weapon to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedWeapon
        """
        if self.userCanAffordItemObj(user, requestedWeapon):
            self.weaponsStock.removeItem(requestedWeapon)
            user.credits -= requestedWeapon.getValue()
            user.inactiveModules.addItem(requestedWeapon)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy weapon " + requestedWeapon.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedWeapon.getValue()))


    def userSellWeaponObj(self, user : basedUser.BasedUser, weapon : primaryWeapon.PrimaryWeapon):
        """Buy the given weapon from the given user,
        adding the appropriate credits to their balance and adding the weapon to the shop stock.

        :param basedUser user: The user to buy weapon from
        :param primaryWeapon weapon: The weapon to buy from user
        """
        user.credits += weapon.getValue()
        self.weaponsStock.addItem(weapon)
        user.inactiveWeapons.removeItem(weapon)


    def userSellWeaponIndex(self, user : basedUser.BasedUser, index : int):
        """Buy the weapon at the given index in the given user's weapons inventory,
        adding the appropriate credits to their balance and adding the weapon to the shop stock.

        :param basedUser user: The user to buy weapon from
        :param int index: The index of the weapon to buy from user, in the user's weapons inventory's array of keys
        """
        self.userSellWeaponObj(user, user.inactiveWeapons[index].item)


    ##### MODULE MANAGEMENT #####


    def userCanAffordModuleIndex(self, user : basedUser.BasedUser, index : int) -> bool:
        """Decide whether a user can afford to buy a module from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the module whose value to check, in the shop's module inventory's array of keys
        :return: True if user can afford to buy module number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.modulesStock[index].item)


    def userBuyModuleIndex(self, user : basedUser.BasedUser, index : int):
        """Sell the module at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the module
        :param int index: The index of the requested module in the shop's modules inventory's array of keys
        """
        self.userBuyModuleObj(user, self.modulesStock[index].item)


    def userBuyModuleObj(self, user : basedUser.BasedUser, requestedModule : moduleItem.ModuleItem):
        """Sell the given module to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the module
        :param moduleItem requestedModule: The module to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedModule
        """
        if self.userCanAffordItemObj(user, requestedModule):
            self.modulesStock.removeItem(requestedModule)
            user.credits -= requestedModule.getValue()
            user.inactiveShips.addItem(requestedModule)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy module " + requestedModule.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedModule.getValue()))


    def userSellModuleObj(self, user : basedUser.BasedUser, module : moduleItem.ModuleItem):
        """Buy the given module from the given user,
        adding the appropriate credits to their balance and adding the module to the shop stock.

        :param basedUser user: The user to buy module from
        :param moduleItem module: The module to buy from user
        """
        user.credits += module.getValue()
        self.modulesStock.addItem(module)
        user.inactiveModules.removeItem(module)


    def userSellModuleIndex(self, user : basedUser.BasedUser, index : int):
        """Buy the module at the given index in the given user's modules inventory,
        adding the appropriate credits to their balance and adding the module to the shop stock.

        :param basedUser user: The user to buy module from
        :param int index: The index of the module to buy from user, in the user's modules inventory's array of keys
        """
        self.userSellModuleObj(user, user.inactiveModules[index].item)


    ##### TURRET MANAGEMENT #####


    def userCanAffordTurretIndex(self, user : basedUser.BasedUser, index : int) -> bool:
        """Decide whether a user can afford to buy a turret from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the turret whose value to check, in the shop's turret inventory's array of keys
        :return: True if user can afford to buy turret number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.turretsStock[index].item)


    def userBuyTurretIndex(self, user : basedUser.BasedUser, index : int):
        """Sell the turret at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the turret
        :param int index: The index of the requested turret in the shop's turrets inventory's array of keys
        """
        self.userBuyTurretObj(user, self.turretsStock[index].item)


    def userBuyTurretObj(self, user : basedUser.BasedUser, requestedTurret : turretWeapon.TurretWeapon):
        """Sell the given turret to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the turret
        :param turretWeapon requestedTurret: The turret to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedTurret
        """
        if self.userCanAffordItemObj(user, requestedTurret):
            self.turretsStock.removeItem(requestedTurret)
            user.credits -= requestedTurret.getValue()
            user.inactiveTurrets.addItem(requestedTurret)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy turret " + requestedTurret.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedTurret.getValue()))


    def userSellTurretObj(self, user : basedUser.BasedUser, turret : turretWeapon.TurretWeapon):
        """Buy the given turret from the given user,
        adding the appropriate credits to their balance and adding the turret to the shop stock.

        :param basedUser user: The user to buy turret from
        :param turretWeapon turret: The turret to buy from user
        """
        user.credits += turret.getValue()
        self.turretsStock.addItem(turret)
        user.inactiveTurrets.removeItem(turret)


    def userSellTurretIndex(self, user : basedUser.BasedUser, index : int):
        """Buy the turret at the given index in the given user's turrets inventory,
        adding the appropriate credits to their balance and adding the turret to the shop stock.

        :param basedUser user: The user to buy turret from
        :param int index: The index of the turret to buy from user, in the user's turrets inventory's array of keys
        """
        self.userSellTurretObj(user, user.inactiveTurrets[index].item)


    ##### TOOL MANAGEMENT #####


    def userCanAffordToolIndex(self, user : basedUser.BasedUser, index : int) -> bool:
        """Decide whether a user can afford to buy a tool from the shop's stock
        :param BasedUser user: The user whose credits balance to check
        :param int index: The index of the tool whose value to check, in the shop's tool Inventory's array of keys
        :return: True if user can afford to buy tool number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.toolsStock[index].item)


    def userBuyToolIndex(self, user : basedUser.BasedUser, index : int):
        """Sell the tool at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.
        :param BasedUser user: The user attempting to buy the tool
        :param int index: The index of the requested tool in the shop's tools Inventory's array of keys
        """
        self.userBuyToolObj(user, self.toolsStock[index].item)


    def userBuyToolObj(self, user : basedUser.BasedUser, requestedTool : toolItem.ToolItem):
        """Sell the given tool to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.
        :param BasedUser user: The user attempting to buy the tool
        :param ToolItem requestedTool: The tool to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedTool
        """
        if self.userCanAffordItemObj(user, requestedTool):
            self.toolsStock.removeItem(requestedTool)
            user.credits -= requestedTool.getValue()
            user.inactiveTools.addItem(requestedTool)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy tool " + requestedTool.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedTool.getValue()))


    def userSellToolObj(self, user : basedUser.BasedUser, tool : toolItem.ToolItem):
        """Buy the given tool from the given user,
        adding the appropriate credits to their balance and adding the tool to the shop stock.
        :param BasedUser user: The user to buy tool from
        :param bbTool tool: The tool to buy from user
        """
        user.credits += tool.getValue()
        self.toolsStock.addItem(tool)
        user.inactiveTools.removeItem(tool)


    def userSellToolIndex(self, user : basedUser.BasedUser, index : int):
        """Buy the tool at the given index in the given user's tools Inventory,
        adding the appropriate credits to their balance and adding the tool to the shop stock.
        :param BasedUser user: The user to buy tool from
        :param int index: The index of the tool to buy from user, in the user's tools Inventory's array of keys
        """
        self.userSellToolObj(user, user.inactiveTools[index].item)


    ##### SERIALIZING #####


    def toDict(self, **kwargs) -> dict:
        """Get a dictionary containing all information needed to reconstruct this shop instance.
        This includes maximum item counts, and current stocks.

        :return: A dictionary containing all information needed to reconstruct this shop object
        :rtype: dict
        """
        if "saveType" not in kwargs or not kwargs["saveType"]:
            kwargs["saveType"] = True

        data = {}
        for invType in ["ship", "weapon", "module", "turret", "tool"]:
            stockDict = []
            currentStock = self.getStockByName(invType)

            for currentItem in currentStock.keys:
                if currentItem in currentStock.items:
                    stockDict.append(currentStock.items[currentItem].toDict(**kwargs))
                else:
                    botState.logger.log("bbShp", "toDict",
                                "Failed to save invalid " + invType + " key '" + str(currentItem) \
                                    + "' - not found in items dict",
                                category="shop", eventType="UNKWN_KEY")

            data[invType + "sStock"] = stockDict

        return data


    @classmethod
    def fromDict(cls, shopDict : dict, **kwargs) -> GuildShop:
        """Recreate a guildShop instance from its dictionary-serialized representation - the opposite of guildShop.toDict

        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new guildShop object as described by shopDict
        :rtype: guildShop
        """
        shipsStock = inventory.TypeRestrictedInventory(shipItem.Ship)
        weaponsStock = inventory.TypeRestrictedInventory(primaryWeapon.PrimaryWeapon)
        modulesStock = inventory.TypeRestrictedInventory(moduleItem.ModuleItem)
        turretsStock = inventory.TypeRestrictedInventory(turretWeapon.TurretWeapon)
        toolsStock = inventory.TypeRestrictedInventory(toolItem.ToolItem)

        if "shipsStock" in shopDict:
            for shipListingDict in shopDict["shipsStock"]:
                shipsStock.addItem(shipItem.Ship.fromDict(shipListingDict["item"]), quantity=shipListingDict["count"])

        if "weaponsStock" in shopDict:
            for weaponListingDict in shopDict["weaponsStock"]:
                weaponsStock.addItem(primaryWeapon.PrimaryWeapon.fromDict(weaponListingDict["item"]),
                                        quantity=weaponListingDict["count"])

        if "modulesStock" in shopDict:
            for moduleListingDict in shopDict["modulesStock"]:
                modulesStock.addItem(moduleItemFactory.fromDict(moduleListingDict["item"]),
                                        quantity=moduleListingDict["count"])

        if "turretsStock" in shopDict:
            for turretListingDict in shopDict["turretsStock"]:
                turretsStock.addItem(turretWeapon.TurretWeapon.fromDict(turretListingDict["item"]),
                                        quantity=turretListingDict["count"])

        if "toolsStock" in shopDict:
            for toolListingDict in shopDict["toolsStock"]:
                toolsStock.addItem(toolItemFactory.fromDict(toolListingDict["item"]), quantity=toolListingDict["count"])

        return GuildShop(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                            turretsStock=turretsStock, toolsStock=toolsStock)


class TechLeveledShop(GuildShop):
    """A shop containing a random selection of items which players can buy.
    Items can be sold to the shop to the shop's inventory and listed for sale.
    Shops are assigned a random tech level, which influences ths stock generated.
    
    :var currentTechLevel: The current tech level of the shop, influencing the tech levels of the stock generated upon refresh.
    :vartype currentTechLevel: int
    """

    def __init__(self, shipsStock : inventory.Inventory = inventory.TypeRestrictedInventory(shipItem.Ship),
            weaponsStock : inventory.Inventory = inventory.TypeRestrictedInventory(primaryWeapon.PrimaryWeapon),
            modulesStock : inventory.Inventory = inventory.TypeRestrictedInventory(moduleItem.ModuleItem),
            turretsStock : inventory.Inventory = inventory.TypeRestrictedInventory(turretWeapon.TurretWeapon),
            toolsStock : inventory.Inventory = inventory.TypeRestrictedInventory(toolItem.ToolItem),
            currentTechLevel : int = cfg.minTechLevel, noRefresh : bool = False):
        """
        :param int currentTechLevel: The current tech level of the shop, influencing the tech levels of the stock generated
                                        upon refresh. (Default empty inventory)
        :param inventory shipsStock: The shop's current stock of ships (Default empty inventory)
        :param inventory weaponsStock: The shop's current stock of weapons (Default empty inventory)
        :param inventory modulesStock: The shop's current stock of modules (Default empty inventory)
        :param inventory turretsStock: The shop's current stock of turrets (Default empty inventory)
        :param inventory toolsStock: The shop's current stock of tools (Default empty inventory)
        :param bool noRefresh: By default, if all shop stocks are empty, the shop will refresh. Give True here to disable this
                                functionality and allow empty shops. (Default False)
        """
        super().__init__(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock, turretsStock=turretsStock, toolsStock=toolsStock)

        self.currentTechLevel = currentTechLevel
        if (not noRefresh) and shipsStock.isEmpty() and weaponsStock.isEmpty() and modulesStock.isEmpty() and turretsStock.isEmpty():
            self.refreshStock()


    def refreshStock(self, level : int = -1):
        """Refresh the stock of the shop by picking random items according to the given tech level. All previous stock is deleted.
        If level = -1 is given, a new shop tech level is generated at random.

        :param int level: The new tech level of the shop. Give -1 to pick a level at random according to cfg.pickRandomShopTL()
        :raise ValueError: When given a tech level that is out of range
        """
        self.shipsStock.clear()
        self.weaponsStock.clear()
        self.modulesStock.clear()
        self.turretsStock.clear()
        self.toolsStock.clear()

        if level == -1:
            self.currentTechLevel = gameMaths.pickRandomShopTL()
        else:
            if level not in range(cfg.minTechLevel, cfg.maxTechLevel + 1):
                raise ValueError("Attempted to refresh a shop at tech level " + str(level) + ". must be within the range " \
                                    + str(cfg.minTechLevel) + " to " + str(cfg.maxTechLevel))
            self.currentTechLevel = level

        for maxCount, stock, keys in (  (cfg.shopDefaultModulesNum, self.modulesStock, bbData.moduleObjsByTL),
                                        (cfg.shopDefaultWeaponsNum, self.weaponsStock, bbData.weaponObjsByTL),
                                        (cfg.shopDefaultTurretsNum, self.turretsStock, bbData.turretObjsByTL),
                                        (cfg.shopDefaultToolsNum,   self.toolsStock,   bbData.toolObjsByTL)):
            for _ in range(maxCount):
                itemTL = cfg.pickRandomItemTL(self.currentTechLevel)
                if len(keys[itemTL - 1]) != 0:
                    stock.addItem(random.choice(keys[itemTL - 1]))

        for _ in range(cfg.shopDefaultShipsNum):
            itemTL = cfg.pickRandomItemTL(self.currentTechLevel)
            if len(bbData.shipKeysByTL[itemTL - 1]) != 0:
                newShip = shipItem.Ship.fromDict(bbData.builtInShipData[random.choice(bbData.shipKeysByTL[itemTL - 1])])
                self.shipsStock.addItem(newShip)


    def toDict(self, **kwargs) -> dict:
        """Get a dictionary containing all information needed to reconstruct this shop instance.
        This includes maximum item counts, current tech level, and current stocks.

        :return: A dictionary containing all information needed to reconstruct this shop object
        :rtype: dict
        """
        data = super().toDict(**kwargs)
        data["currentTechLevel"] = self.currentTechLevel
        return data


    @classmethod
    def fromDict(cls, shopDict : dict, **kwargs) -> TechLeveledShop:
        """Recreate a TechLeveledShop instance from its dictionary-serialized representation - the opposite of TechLeveledShop.toDict
        
        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new TechLeveledShop object as described by shopDict
        :rtype: TechLeveledShop
        """
        shipsStock = inventory.TypeRestrictedInventory(shipItem.Ship)
        weaponsStock = inventory.TypeRestrictedInventory(primaryWeapon.PrimaryWeapon)
        modulesStock = inventory.TypeRestrictedInventory(moduleItem.ModuleItem)
        turretsStock = inventory.TypeRestrictedInventory(turretWeapon.TurretWeapon)
        toolsStock = inventory.TypeRestrictedInventory(toolItem.ToolItem)

        if "shipsStock" in shopDict:
            for shipListingDict in shopDict["shipsStock"]:
                shipsStock.addItem(shipItem.Ship.fromDict(shipListingDict["item"]), quantity=shipListingDict["count"])

        if "weaponsStock" in shopDict:
            for weaponListingDict in shopDict["weaponsStock"]:
                weaponsStock.addItem(primaryWeapon.PrimaryWeapon.fromDict(weaponListingDict["item"]),
                                                                            quantity=weaponListingDict["count"])

        if "modulesStock" in shopDict:
            for moduleListingDict in shopDict["modulesStock"]:
                modulesStock.addItem(moduleItemFactory.fromDict(moduleListingDict["item"]),
                                                                quantity=moduleListingDict["count"])

        if "turretsStock" in shopDict:
            for turretListingDict in shopDict["turretsStock"]:
                turretsStock.addItem(turretWeapon.TurretWeapon.fromDict(turretListingDict["item"]),
                                                                        quantity=turretListingDict["count"])

        if "toolsStock" in shopDict:
            for toolListingDict in shopDict["toolsStock"]:
                toolsStock.addItem(toolItemFactory.fromDict(toolListingDict["item"]), quantity=toolListingDict["count"])

        return TechLeveledShop(currentTechLevel=shopDict["currentTechLevel"] if "currentTechLevel" in shopDict else 1,
                                shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                                turretsStock=turretsStock, toolsStock=toolsStock)
