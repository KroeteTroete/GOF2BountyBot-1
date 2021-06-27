from PIL import Image, ImageDraw
from typing import Dict, Union, Tuple
from ..cfg import cfg
import atexit


XP_BAR_SILHOUETTE: Image.Image = None
XP_BAR_BACKGROUNDS: Dict[str, Image.Image] = {}
XP_BAR_FILLS: Dict[str, Image.Image] = {}


def closeAll():
    """Close all active graphics. Should only be used for shutdown.
    """
    if XP_BAR_SILHOUETTE is not None:
        XP_BAR_SILHOUETTE.close()
    for im in XP_BAR_BACKGROUNDS.values():
        im.close()
    for im in XP_BAR_FILLS.values():
        im.close()


# Automatically close all images when the module is unimported
atexit.register(closeAll)


def progressBar(w: int, h: int, progress: float, mode: str = "1", bgColour: Union[str, int, Tuple[int]] = 0,
        barColour: Union[str, int, Tuple[int]] = 1) -> Image.Image:
    """Create a simple progress bar with a black background. Background fills the image, not limited to the bar shape.
    The default image mode is "1" - single-bit images intended to be used for creating image masks.
    Changes to this should be reflected in bgColour and colour

    Adapted from https://www.programmersought.com/article/71441110786/

    :param int w: The image width
    :param int h: The image height
    :param str mode: The image mode (Default 1)
    :param float progress: Percentage progress of the bar between 0 and 1
    :param bgColour: Colour for the background of the whole image. The type of this parameter depends on pil_image.mode
                        (default black)
    :type bgColour: Union[str, int, Tuple[int]]
    :param barColour: Colour to fill the bar with. The type of this parameter depends on pil_image.mode (default white)
    :type barColour: Union[str, int, Tuple[int]]
    """
    im = Image.new(mode, (w, h), bgColour)
    drawObject = ImageDraw.Draw(im)
    w = w * min(1, max(0.01, progress))

    drawObject.ellipse(  ((0, 0),     (h, h)),         fill=barColour)
    drawObject.ellipse(  ((w - h, 0), (w, h)),         fill=barColour)
    drawObject.rectangle(((h / 2, 0), (w - h / 2, h)), fill=barColour)

    return im


def copyXPBarSilhouette() -> Image.Image:
    """Get a copy of the image to place behind XP bars - the "silhouette".
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :return: An image containing a full progress bar silhouette, to be pasted behind an XP progress bar.
    :rtype: Image.Image
    """
    global XP_BAR_SILHOUETTE
    if XP_BAR_SILHOUETTE is None:
        XP_BAR_SILHOUETTE = progressBar(cfg.xpBarWidth, cfg.xpBarHeight, 1, "RGBA", 0, cfg.xpBarSilhouetteColour)
    return XP_BAR_SILHOUETTE.copy()


def copyXPBarFill(divName: str) -> Image.Image:
    """Get a copy of the image to mask when filling an XP progress bar.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :param str divName: The name of the division whose image to fetch
    :return: An image containing the file referenced in cfg for the named division, but scaled to the correct dimensions.
    :rtype: Image.Image
    """
    global XP_BAR_FILLS
    if XP_BAR_FILLS == {}:
        pathsDone: Dict[str, Image.Image] = {}
        for div, fillPath in cfg.xpBarFill.items():
            if fillPath in pathsDone:
                XP_BAR_FILLS[div] = pathsDone[fillPath]
            else:
                XP_BAR_FILLS[div] = Image.open(fillPath)
                XP_BAR_FILLS[div] = XP_BAR_FILLS[div].resize((cfg.xpBarWidth, cfg.xpBarHeight))

    return XP_BAR_FILLS[divName].copy()


def copyXPBarBackground(divName: str) -> Image.Image:
    """Get a copy of the image to place behind both the XP bar and the silhouette.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :param str divName: The name of the division whose image to fetch
    :return: An image containing a full progress bar background, to be pasted behind an XP progress bar and silhouette.
    :rtype: Image.Image
    """
    global XP_BAR_BACKGROUNDS
    if XP_BAR_BACKGROUNDS == {}:
        pathsDone: Dict[str, Image.Image] = {}
        for div, fillPath in cfg.xpBarBackground.items():
            if fillPath in pathsDone:
                XP_BAR_BACKGROUNDS[div] = pathsDone[fillPath]
            else:
                XP_BAR_BACKGROUNDS[div] = Image.open(fillPath)
                XP_BAR_BACKGROUNDS[div] = XP_BAR_BACKGROUNDS[div].resize((cfg.xpBarWidth, cfg.xpBarHeight))

    return XP_BAR_BACKGROUNDS[divName].copy()


def padImage(pil_img: Image.Image, top: int, right: int, bottom: int, left: int,
        colour: Union[str, int, Tuple[int]]) -> Image.Image:
    """Pads an image, placing extra space around it and filling that space with the given colour.
    This is done by creating a new image, the original is not modified.

    https://note.nkmk.me/en/python-pillow-add-margin-expand-canvas/

    :param Image.Image pil_Image: The original image
    :param int top: Amount of extra space to add on top of the image, in pixels
    :param int right: Amount of extra space to add on the right of the image, in pixels
    :param int bottom: Amount of extra space to add beneith the image, in pixels
    :param int left: Amount of extra space to add on the left of the image, in pixels
    :param colour: Colour to fill the new empty space with. The type of this parameter depends on pil_image.mode
    :type colour: Union[str, int, Tuple[int]]
    """
    result = Image.new(pil_img.mode, (pil_img.size[0] + right + left, pil_img.size[1] + top + bottom), colour)
    result.paste(pil_img, (left, top))
    return result
