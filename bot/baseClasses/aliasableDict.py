from .aliasable import Aliasable
from typing import Any


class AliasableDict(dict):
    """A dictionary where keys are guaranteed to be Aliasable subclasses.
    """

    def getKeyNamed(self, name: str) -> Aliasable:
        """Search the dictionary for a key with the given name or alias.

        :param str name: The name or alias to look up
        :return: A key registered in the dictionary with name as either its name or one of its aliases
        :rtype: Aliasable
        :raise KeyError: If no key in the dictionary is called name
        :raise TypeError: If name is not a str
        """
        if type(name) != str:
            raise TypeError("Expecting type str for parameter name, received '" + type(name).__name__ + "'")
        for k in self:
            if k.isCalled(name):
                return k
        raise KeyError("Could not find a key with the given name: " + name)


    def getValueForKeyNamed(self, name: str) -> Any:
        """Search the dictionary for a key with the given name or alias, and get the value paired with it.

        :param str name: The name or alias to look up
        :return: A value which is paired with a registered key where name is either its name or one of its aliases
        :rtype: Any
        :raise KeyError: If no key in the dictionary is called name
        :raise TypeError: If name is not a str
        """
        return self[self.getKeyNamed(name)]


    def __setitem__(self, k: Aliasable, v: Any) -> None:
        """Register a key value pair, or change the value of an existing pair. k must be an Aliasable.

        :param Aliasable k: The key to register, or change the value of
        :param Any v: The value to register to key k
        :raise TypeError: If k is not an Aliasable
        """
        if not isinstance(k, Aliasable):
            raise TypeError("Keys must be Aliasable, given " + type(k).__name__)
        super().__setitem__(k, v)


    def add(self, k: Aliasable) -> None:
        """Register a key value pair, or change the value of an existing pair. k must be an Aliasable.
        The key to register is inferred as k.name

        :param Aliasable k: The key to register, or change the value of
        """
        self[k.name] = k
