from .serializable import Serializable

class Unlockable(Serializable):
    """Something which is owned by users, but is not an item. Cannot be spawned or traded,
    more like a user attribute.
    """

    def __init__(self):
        super().__init__()