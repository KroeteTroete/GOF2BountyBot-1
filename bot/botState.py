class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


client = None

usersDB = None
guildsDB = None
reactionMenusDB = None

newBountiesTTDB = None
duelRequestTTDB = None
shopRefreshTT = None

logger = None

dbSaveTT = None

# Reaction Menus
reactionMenusDB = None
reactionMenusTTDB = None

shutdown = ShutDownState.restart

updatesCheckTT = None

# Scheduling overrides
newBountyFixedDeltaChanged = False


# Names of ships currently being rendered
currentRenders = []
