# Typing imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..users import basedUser

from .items import moduleItemFactory, shipItem
from .items.weapons import primaryWeapon, turretWeapon
from .items.modules import moduleItem
from .inventories import inventory
from .items.tools import toolItem, toolItemFactory
from . import guildShop, itemDiscount


class LomaShop(guildShop.GuildShop):
    """A private shop unique to each player, for purchasing special items intended only for that player.
    Items cannot be sold to Loma.
    """


    def userSellShipObj(self, user : basedUser.BasedUser, ship : shipItem.Ship):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellShipIndex(self, user : basedUser.BasedUser, index : int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellWeaponObj(self, user : basedUser.BasedUser, weapon : primaryWeapon.PrimaryWeapon):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellWeaponIndex(self, user : basedUser.BasedUser, index : int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellModuleObj(self, user : basedUser.BasedUser, module : moduleItem.ModuleItem):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellModuleIndex(self, user : basedUser.BasedUser, index : int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellTurretObj(self, user : basedUser.BasedUser, turret : turretWeapon.TurretWeapon):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellTurretIndex(self, user : basedUser.BasedUser, index : int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellToolObj(self, user : basedUser.BasedUser, tool : toolItem.ToolItem):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellToolIndex(self, user : basedUser.BasedUser, index : int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    @classmethod
    def fromDict(cls, shopDict : dict, **kwargs) -> LomaShop:
        """Recreate a bbShop instance from its dictionary-serialized representation - the opposite of bbShop.toDict
        
        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new bbShop object as described by shopDict
        :rtype: bbShop
        """
        shipsStock = inventory.DiscountableTypeRestrictedInventory(shipItem.Ship)
        weaponsStock = inventory.DiscountableTypeRestrictedInventory(primaryWeapon.PrimaryWeapon)
        modulesStock = inventory.DiscountableTypeRestrictedInventory(moduleItem.ModuleItem)
        turretsStock = inventory.DiscountableTypeRestrictedInventory(turretWeapon.TurretWeapon)
        toolsStock = inventory.DiscountableTypeRestrictedInventory(toolItem.ToolItem)

        for key, stock, deserializer in (("shipsStock", shipsStock, shipItem.Ship.fromDict),
                                        ("weaponsStock", weaponsStock, primaryWeapon.PrimaryWeapon.fromDict),
                                        ("modulesStock", modulesStock, moduleItemFactory.fromDict),
                                        ("turretsStock", turretsStock, turretWeapon.TurretWeapon.fromDict),
                                        ("toolsStock", toolsStock, toolItemFactory.fromDict)):
            if key in shopDict:
                for listingDict in shopDict[key]:
                    newItem = deserializer(listingDict["item"], **kwargs)
                    stock.addItem(newItem, quantity=listingDict["count"])
                    if "discounts" in listingDict:
                        for discountDict in listingDict["discounts"]:
                            stock.getListing(newItem).pushDiscount(itemDiscount.ItemDiscount.fromDict(discountDict, **kwargs))

        return LomaShop(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                        turretsStock=turretsStock, toolsStock=toolsStock)