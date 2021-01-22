from ..lib.emojis import UninitializedBasedEmoji

# All emojis used by the bot
defaultEmojis = {
    "longProcess": UninitializedBasedEmoji("⏳"),
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    "dmSent": UninitializedBasedEmoji("📬"),
    "cancel": UninitializedBasedEmoji("🇽"),
    "submit": UninitializedBasedEmoji("✅"),
    "spiral": UninitializedBasedEmoji("🌀"),
    "error": UninitializedBasedEmoji("❓"),
    "accept": UninitializedBasedEmoji("👍"),
    "reject": UninitializedBasedEmoji("👎"),
    "next": UninitializedBasedEmoji('⏩'),
    "previous": UninitializedBasedEmoji('⏪'),
    "numbers": [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")],

    # The default emojis to list in a reaction menu
    "menuOptions": [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                    UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                    UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                    UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")]
}

timeouts = {
    "helpMenu": {"minutes": 3},
    "BASED_updateCheckFrequency": {"days": 1},
    # The time to wait inbetween database autosaves.
    "dataSaveFrequency": {"hours": 1},

    # Amount of time before a duel request expires
    "duelRequest": {"days": 1},

    # Amount of time to wait between refreshing stock of all shops
    "shopRefresh": {"days": 0, "hours": 6, "minutes": 0, "seconds": 0},

    # time to put users on cooldown between using !bb check
    "checkCooldown": {"minutes":3}
}

paths = {
    # path to JSON files for database saves
    "usersDB": "saveData" + "/" + "users.json",
    "guildsDB": "saveData" + "/" + "guilds.json",
    "reactionMenusDB": "saveData" + "/" + "reactionMenus.json",

    # path to folder to save log txts to
    "logsFolder": "saveData" + "/" + "logs",

    # folder to store temporary render files in, e.g intermediary images, renderer config files
    "rendererTempFolder": "rendering-temp"
}


##### COMMANDS #####

# Names of user access levels to be used in help menus.
# Also determines the number of access levels available, e.g when registering commands
userAccessLevels = ["user", "mod", "admin", "dev"]

# Message to print alongside cmd_help menus
helpIntro = "Here are my commands!"

# Maximum number of commands each cmd_help menu may contain
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
includedCommandModules = ("usr_misc",
                          "admn_misc",
                          "dev_misc")
                          
"""includedCommandModules = (  "usr_misc", "usr_homeguilds", "usr_gof2-info", "usr_bounties", "usr_loadout", "usr_economy",
                            "admn_channels", "admn_misc",
                            "dev_misc", "dev_channels", "dev_bounties", "dev_items", "dev_skins")"""

# Default prefix for commands
defaultCommandPrefix = "."



##### REACTION MENUS #####

# Text to edit into expired menu messages
expiredMenuMsg = "😴 This role menu has now expired."



##### SCHEDULING #####

# Can currently only be "fixed"
timedTaskCheckingType = "fixed"
# Number of seconds by with the expiry of a timedtask may acceptably be late
timedTaskLatenessThresholdSeconds = 10

# Whether or not to check for updates to BASED
BASED_checkForUpdates = True



##### ADMINISTRATION #####

# discord user IDs of developers - will be granted developer command permissions
developers = [188618589102669826]



##### GAME MATHS #####

# Number of decimal places to calculate itemTLSpawnChanceForShopTL values to
itemSpawnRateResDP = 3

# The range of valid tech levels a shop may spawn at
minTechLevel = 1
maxTechLevel = 10



##### DUELS #####

# The amount to vary ship stats (+-) by before executing a duel
duelVariancePercent = 0.05

# Max number of entries that can be printed for a duel log
duelLogMaxLength = 10

# Percentage probability of a user envoking a cloak module in a given timeStep, should they have one equipped
duelCloakChance = 20



##### SHOPS #####

# The number of ranks to use when randomly picking shop stock
numShipRanks = 10
numWeaponRanks = 10
numModuleRanks = 7
numTurretRanks = 3

# The default number of items shops should generate every shopRefreshStockPeriod
shopRefreshShips = 5
shopRefreshWeapons = 5
shopRefreshModules = 5
shopRefreshTurrets = 2

# bbTurret is the only item that has a probability not to be spawned.
# This metric indicates the percentage chance of turrets being stocked on a given refresh
turretSpawnProbability = 45



##### BOUNTIES #####

# Maximum number of bounties that may simulatneously be available, per fection
maxBountiesPerFaction = 5

# The maximum number of bounties a player is allowed to win each day
maxDailyBountyWins = 10

# can be "fixed" or "random"
newBountyDelayType = "random-routeScale"

### Fixed delay config
# only spawn bounties at this time of day.
newBountyFixedDailyTime = {"hours":18, "minutes":40, "seconds":0}

# time to wait inbetween spawning bounties
# when using fixed-routeScale generation, use this for bounties of route length 1
newBountyFixedDelta = {"days":0, "hours":0, "minutes":1, "seconds":0}

### random delay config
# when using random delay generation, use these min and max points
# when using random-routeScale generation, use these min and max points for bounties of route length 1
newBountyDelayRandomRange = {"min": 5 * 60, "max": 7 * 60}

### routeScale config
newBountyDelayRouteScaleCoefficient = 1
fallbackRouteScale = 5


# The number of credits to award for each bPoint (each system in a criminal route)
bPointsToCreditsRatio = 1000

# number of bounties ahead of a checked system in a route to report a recent criminal spotting (+1)
closeBountyThreshold = 4

# Text to send to a BountyBoardChannel when no bounties are currently active
bbcNoBountiesMsg = "```css\n[ NO ACTIVE BOUNTIES ]\n\nThere are currently no active bounty listings.\n" + \
                    "Please check back later, or use [ $notify bounties ] to be pinged when new ones become available!\n```"

# The number of times to retry API calls when HTTP exceptions are thrown
httpErrRetries = 3

# The number of seconds to wait between API call retries upon HTTP exception catching
httpErrRetryDelaySeconds = 1



##### MISC #####

# Exactly one of botToken or botToken_envVarName must be given.
# botToken contains a string of your bot token
# botToken_envVarName contains the name of an environment variable to get your bot token from
botToken = ""
botToken_envVarName = ""
