from PIL import Image, ImageDraw
from typing import Dict, Union, Tuple
from ..cfg import cfg
import atexit


XP_BAR_SILHOUETTE: Image.Image = None
USR_PROF_BACKGROUND: Image.Image = None
XP_BAR_FILLS: Dict[str, Image.Image] = {}


def closeAll():
    """Close all active graphics. Should only be used for shutdown.
    """
    if XP_BAR_SILHOUETTE is not None:
        XP_BAR_SILHOUETTE.close()
    if USR_PROF_BACKGROUND is not None:
        USR_PROF_BACKGROUND.close()
    for im in XP_BAR_FILLS.values():
        im.close()


# Automatically close all images when the module is unimported
atexit.register(closeAll)


def cropAndScale(baseImage: Image.Image, w: int, h: int):
    """Crop baseImage to match the aspect ratio of (w, h), and then scale the result to match (w, h).
    Cropping is performed from the top-left of the image. The original image is not altered, a new one is created.

    :param Image.Image baseImage: Image to crop/resize
    :param int w: The desired new image width (px)
    :param int h: The desired new image height (px)
    :return: A copy of baseImage, resized to (w, h), but by cropping instead of stretching
    :rtype: Image.Image
    """
    # If sizes are the same, do nothing
    if baseImage.size == (w, h):
        return baseImage

    # If aspect ratios are different, crop
    if baseImage.width / baseImage.height != w / h:
        # Crop the longest side
        if baseImage.width < baseImage.height:
            desiredHeight = (w / baseImage.width) * h
            newImage = baseImage.crop(0, baseImage.width, 0, desiredHeight)
        else:
            desiredwidth = (h / baseImage.height) * w
            newImage = baseImage.crop(0, desiredwidth, 0, baseImage.height)

        # If no scaling is needed, return cropped image
        if newImage.width == w:
            return newImage
    else:
        newImage = baseImage

    # Scale image
    return newImage.resize((w, h))


def applyProgressBarOutline(progressBar: Image.Image, progress: float, emptyColour: Union[str, int, Tuple[int]],
        lineColour: Union[str, int, Tuple[int]] = (255, 255, 255), lineWidth: int = 1):
    """Apply an outline in the shape of a progress bar, over the given image. The operation is performed on a new image,
    the orignal is not modified. The given image should contain only the bar and nothing else,
    as provided by the progressBar function below.

    :param Image.Image progressBar: The image to apply the outline to
    :param float progress: Percentage progress of the bar between 0 and 1
    :param emptyColour: Colour to fill empty space with
    :type emptyColour: Union[str, int, Tuple[int]]
    :param lineColour: The colour of the outline (Default white)
    :type lineColour: Union[str, int, Tuple[int]]
    :param int lineWidth: The width of the outline in pixels (Default 1)
    :return: progressBar, with an outline drawn around the bar
    :rtype: Image.Image
    """
    w, h = progressBar.size
    progressBar = padImage(progressBar, 0, 0, cfg.xpBarOutlineWidth, 0, emptyColour)
    w *= min(1, max(0.01, progress))
    w -= 1
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(progressBar)
    draw.arc(((0, 0),     (h, h)), 90, 270,  fill=lineColour, width=lineWidth)
    draw.arc(((w - h, 0), (w, h)), 270, 450, fill=lineColour, width=lineWidth)
    draw.line(((h / 2, 0), (w - h / 2, 0)), fill=lineColour, width=lineWidth)
    draw.line(((h / 2, h), (w - h / 2, h)), fill=lineColour, width=lineWidth)
    return progressBar


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
    w *= min(1, max(0.01, progress))

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
        print("xpBarSilhouetteColour",cfg.xpBarSilhouetteColour)
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


def copyUserProfileBackground() -> Image.Image:
    """Get a copy of the image to place behind user profile images.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :return: An image to use as a user profile background.
    :rtype: Image.Image
    """
    global USR_PROF_BACKGROUND
    if USR_PROF_BACKGROUND is None:
        USR_PROF_BACKGROUND = Image.open(cfg.userProfileBackground)
        USR_PROF_BACKGROUND = USR_PROF_BACKGROUND.resize((cfg.userProfileImgWidth, cfg.userProfileImgHeight))

    return USR_PROF_BACKGROUND.copy()


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
