from datetime import timedelta

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


client = None
shutdown = ShutDownState.restart

usersDB = None
guildsDB = None
reactionMenusDB = None

newBountiesTTDB = None
duelRequestTTDB = None
shopRefreshTT = None

taskScheduler = None
logger = None

dbSaveTT = None
updatesCheckTT = None

# Scheduling overrides
newBountyFixedDeltaChanged = False


# Names of ships currently being rendered
currentRenders = []

# timedelta representing the system's offset from UTC time
utcOffset: timedelta = None
