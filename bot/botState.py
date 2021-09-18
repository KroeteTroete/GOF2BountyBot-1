from .logging import Logger
from aiohttp import ClientSession
from datetime import timedelta
from github import Github
from typing import cast

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2

client = None # type: ignore[var-annotated]
shutdown = ShutDownState.restart
httpClient: ClientSession = None
githubClient = cast(Github, None)

usersDB = None
guildsDB = None
reactionMenusDB = None

newBountiesTTDB = None
duelRequestTTDB = None
shopRefreshTT = None

taskScheduler = None
logger: Logger = None

dbSaveTT = None
updatesCheckTT = None

temperatureDecayTT = None

# Scheduling overrides
newBountyFixedDeltaChanged = False


# Names of ships currently being rendered
currentRenders = []

# timedelta representing the system's offset from UTC time
utcOffset: timedelta = None
