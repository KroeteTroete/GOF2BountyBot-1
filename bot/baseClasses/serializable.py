from __future__ import annotations
from abc import ABC, abstractmethod, abstractclassmethod
import inspect
from typing import Dict, Any, Tuple

def get_default_args(func):
    # https://stackoverflow.com/a/12627202
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


class Serializable(ABC):
    _defaults = None

    @abstractmethod
    def toDict(self, **kwargs) -> dict:
        """Serialize this object into dictionary format, to be recreated completely.

        :return: A dictionary containing all information needed to recreate this object
        :rtype: dict
        """
        return {}


    @abstractclassmethod
    def fromDict(cls, data: dict, **kwargs) -> Serializable:
        """Recreate a dictionary-serialized Serializable object

        :param dict data: A dictionary containing all information needed to recreate the serialized object
        :return: A new object as specified by the attributes in data
        :rtype: Serializable
        """
        pass


    def __hash__(self) -> int:
        """Calculate a hash of this object based on its type name and location in memory.

        :return: A unique hash for this object
        :rtype: int
        """
        return hash(repr(self))
    
    @classmethod
    def _makeDefaults(cls, args : Dict[str, Any] = {}, ignores : Tuple[str] = (), **overrides):
        if cls._defaults is None:
            cls._defaults = get_default_args(cls.__init__)
        newArgs = cls._defaults.copy()
        if ignores:
            workingArgs = args.copy()
            for argName in ignores:
                if argName in workingArgs:
                    del workingArgs[argName]
            newArgs.update(workingArgs)
        else:
            newArgs.update(args)
        newArgs.update(overrides)
        return newArgs
