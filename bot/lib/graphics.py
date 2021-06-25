from PIL import Image, ImageDraw

def progressBar(w: int, h: int, progress: float, mode: str = "1", bgColour: int = 0, barColour: int = 1) -> Image.Image:
    """Create a simple progress bar with a black background. Background fills the image, not limited to the bar shape.
    The default image mode is "1" - single-bit images intended to be used for creating image masks.
    Changes to this should be reflected in bgColour and colour

    Adapted from https://www.programmersought.com/article/71441110786/

    :param int w: The image width
    :param int h: The image height
    :param str mode: The image mode (Default 1)
    :param float progress: Percentage progress of the bar between 0 and 1
    :param int bgColour: Colour for the background of the whole image (default black)
    :param int colour: Colour to fill the bar with (default white)
    """
    im = Image.new(mode, (w, h), bgColour)
    drawObject = ImageDraw.Draw(im)
    w = w * min(1, max(0.01, progress))

    drawObject.ellipse(  ((0, 0),     (h, h)),         fill=barColour)
    drawObject.ellipse(  ((w - h, 0), (w, h)),         fill=barColour)
    drawObject.rectangle(((h / 2, 0), (w - h / 2, h)), fill=barColour)

    return im


