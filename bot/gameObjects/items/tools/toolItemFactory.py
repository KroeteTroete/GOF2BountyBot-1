from . import toolItem, shipSkinTool, crateTool


def fromDict(toolDict : dict) -> toolItem.ToolItem:
    """Construct a toolItem from its dictionary-serialized representation.
    This method decodes which tool constructor is appropriate based on the 'type' attribute of the given dictionary.

    :param dict toolDict: A dictionary containing all information needed to construct the required toolItem. Critically,
                            a name, type, and builtIn specifier.
    :return: A new toolItem object as described in toolDict
    :rtype: toolItem.toolItem
    :raise NameError: When toolDict does not contain a 'type' attribute.
    """
    toolTypeConstructors = {"ShipSkinTool": shipSkinTool.ShipSkinTool.fromDict,
                        "CrateTool": crateTool.CrateTool.fromDict}

    if "type" not in toolDict:
        raise NameError("Required dictionary attribute missing: 'type'")
    return toolTypeConstructors[toolDict["type"]](toolDict)
