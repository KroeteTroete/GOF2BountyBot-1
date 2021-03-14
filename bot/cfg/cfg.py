from ..lib.emojis import UninitializedBasedEmoji

# All emojis used by the bot
defaultEmojis = {
    # The emoji that will be used when attempting to display an emoji which the bot cannot access. Make sure this is accessible.
    "unrecognisedEmoji": UninitializedBasedEmoji(779632588243075072),
    # When a message prompts a process that will take a long time (e.g rendering), this will be added to the message reactions
    # It will be removed when the long process is finished.
    "longProcess": UninitializedBasedEmoji("⏳"),
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    "dmSent": UninitializedBasedEmoji("📬"),
    "cancel": UninitializedBasedEmoji("🚫"),
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
                    UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")],

    # Default emoji to assign to shipSkinTool items
    "shipSkinTool": UninitializedBasedEmoji(777166858516299786),

    # Default emoji to assign to bbCrates containing shipSkinTools
    # "skinCrate": UninitializedBasedEmoji(723709178736017419)
    "skinCrate": UninitializedBasedEmoji("🥞"),
    # "defaultCrate": UninitializedBasedEmoji(723709178736017419)
    "defaultCrate": UninitializedBasedEmoji("🥞"),
    
    # Emoji sent with new bounty listings
    # "newBounty": UninitializedBasedEmoji(723709178589347921)
    "newBounty": UninitializedBasedEmoji("🥞")
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
    "checkCooldown": {"minutes": 3},

    # Default amount of time reaction menus should be active for
    "roleMenuExpiry": {"days": 1},
    "duelChallengeMenuExpiry": {"hours": 2},
    "pollMenuExpiry": {"minutes": 5}
}

paths = {
    # path to JSON files for database saves
    "usersDB": "saveData" + "/" + "users.json",
    "guildsDB": "saveData" + "/" + "guilds.json",
    "reactionMenusDB": "saveData" + "/" + "reactionMenus.json",

    # path to folder to save log txts to
    "logsFolder": "saveData" + "/" + "logs",

    # folders containing game objects to load into the game
    "CriminalMETAFolder": "game objects" + "/" + "criminals",
    "shipSkinMETAFolder": "game objects" + "/" + "ship skins",
    "bbShipUpgradesMETAFolder": "game objects" + "/" + "ship upgrades",
    "SolarSystemMETAFolder": "game objects" + "/" + "solar systems",
    "bbCommodityMETAFolder": "game objects" + "/" + "items" + "/" + "commodities",
    "bbModuleMETAFolder": "game objects" + "/" + "items" + "/" + "modules",
    "bbSecondaryMETAFolder": "game objects" + "/" + "items" + "/" + "secondaries",
    "bbShipMETAFolder": "game objects" + "/" + "items" + "/" + "ships",
    "bbWeaponMETAFolder": "game objects" + "/" + "items" + "/" + "weapons",
    "bbTurretMETAFolder": "game objects" + "/" + "items" + "/" + "turrets",
    "bbToolMETAFolder": "game objects" + "/" + "items" + "/" + "tools"
}



##### COMMANDS #####

# Message to print alongside cmd_help menus
helpIntro = "Here are my commands!"

# Maximum number of commands each cmd_help menu may contain
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
# includedCommandModules = ("usr_misc",
#                           "admn_misc",
#                           "dev_misc")

includedCommandModules = (  "usr_misc", "usr_homeguilds", "usr_gof2-info", "usr_bounties", "usr_loadout", "usr_economy",
                            "usr_kaamo", "admn_channels", "admn_misc",
                            "dev_misc", "dev_channels", "dev_bounties", "dev_items", "dev_skins")

# Default prefix for commands
defaultCommandPrefix = "$"



##### REACTION MENUS #####

# Text to edit into expired menu messages
expiredMenuMsg = "😴 This role menu has now expired."
# Length of the bars in poll results bar charts
pollMenuResultsBarLength = 10
# Max number of role menus a guild may own
maxRoleMenusPerGuild = 10
# Amount of time to allow for response to the cmd_use confirmation menu
toolUseConfirmTimeoutSeconds = 60
# Amount of time to allow for response to the cmd_transfer confirmation menu
homeGuildTransferConfirmTimeoutSeconds = 60
# Amount of time to allow for response to the cmd_prestige confirmation menu
prestigeConfirmTimeoutSeconds = 60



##### SCHEDULING #####

# Use "fixed" to check for task expiry every timedTaskLatenessThresholdSeconds (polling-based scheduler)
# Use "dynamic" to check for task expiry exactly at the time of task expiry (interrupts-based scheduler)
timedTaskCheckingType = "dynamic"
# Number of seconds by with the expiry of a timedtask may acceptably be late.
# Regardless of timedTaskCheckingType, this is used for the termination signal checking period.
timedTaskLatenessThresholdSeconds = 10

# Whether or not to check for updates to BASED
BASED_checkForUpdates = True



##### ADMINISTRATION #####

# discord user IDs of developers - will be granted developer command permissions
developers = [188618589102669826, 448491245296418817]

# Names of user access levels to be used in help menus.
# Also determines the number of access levels available, e.g when registering commands
userAccessLevels = ["user", "mod", "admin", "dev"]

# titles to give each type of user when reporting error messages etc
accessLevelTitles = ["pilot", "captain", "commander", "officer"]



##### USERS #####

userAlertsIDsDefaults = {   "bounties_new": False,

                            "shop_refresh": False,

                            "duels_challenge_incoming_new": True,
                            "duels_challenge_incoming_cancel": False,

                            "system_updates_major": False,
                            "system_updates_minor": False,
                            "system_misc": False}

homeGuildTransferCooldown = {"weeks": 1}



##### GAME MATHS #####

# Number of decimal places to calculate itemTLSpawnChanceForShopTL values to
itemSpawnRateResDP = 3

# The range of valid tech levels a shop may spawn at
minTechLevel = 1
maxTechLevel = 10

# Price ranges by which ships should be ranked into tech levels. 0th index = tech level 1
shipMaxPriceTechLevels = [50000, 100000, 200000, 500000, 1000000, 2000000, 5000000, 7000000, 7500000, 999999999]



##### USER LEVELING #####


# Apply a multiplier to all rewards gained from a bounty. bounty hunter xp is thus a measure of
# total earnings from bounty hunting.
bountyRewardToXPGainMult = 0.1



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

# The default number of items shops should generate every timeouts.shopRefresh
shopDefaultShipsNum = 5
shopDefaultWeaponsNum = 5
shopDefaultModulesNum = 5
shopDefaultTurretsNum = 2
shopDefaultToolsNum = 0

# bbTurret is the only item that has a probability not to be spawned.
# This metric indicates the percentage chance of turrets being stocked on a given refresh
turretSpawnProbability = 45

# The number of items users may store in their Kaamo Club.
kaamoMaxCapacity = 70



##### BOUNTIES #####

# Maximum number of bounties that may simulatneously be available, per fection
maxBountiesPerFaction = 5

# The maximum number of bounties a player is allowed to win each day
maxDailyBountyWins = 10

# can be "fixed" or "random"
newBountyDelayType = "random-routeScale"

### Fixed delay config
# only spawn bounties at this time of day.
newBountyFixedDailyTime = {"hours": 18, "minutes": 40, "seconds": 0}

# time to wait inbetween spawning bounties
# when using fixed-routeScale generation, use this for bounties of route length 1
newBountyFixedDelta = {"days": 0, "hours": 0, "minutes": 1, "seconds": 0}

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
bbcNoBountiesMsg = "```css\n[ NO ACTIVE BOUNTIES ]\n\nThere are currently no active bounty listings.\n" \
                    + "Please check back later, or use [ $notify bounties ] to be pinged when new ones become available!\n```"

# The percentage of a criminal's ship value to award to the winner
shipValueRewardPercentage = 0.01

# The probability of a criminal equipping a turret, should their ship have space for one
criminalEquipTurretChance = 30

# The maximum number of levels a criminal's gear may be above their difficulty rating
criminalMaxGearUpgrade = 1

# The maximum total-value a player may have before being disallowed from hunting a tech-level of bounty. 0th index = tech level 1
# I.e, to hunt level 1 bounties, a player must be worth no more than bountyTLMaxPlayerValues[0] credits.
bountyTLMaxPlayerValues = [50000, 75000, 100000, 200000, 450000, 600000, 800000, 1000000, 2000000, 3000000, 999999999]

level0CrimLoadout = {"name": "Betty", "builtIn":True,
                    "weapons":[{"name": "Nirai Impulse EX 1", "builtIn": True}],
                    "modules":[{"name": "Telta Quickscan", "builtIn": True}, {"name": "ZMI Optistore", "builtIn": True},
                                {"name": "IMT Extract 2.7", "builtIn": True}]}



##### SKINS #####

# Discord server containing the skinRendersChannel
mediaServer = 699744305274945650
# Channel to send ship skin renders to and link from
skinRendersChannel = 770036783026667540
# Channel to send showme-prompted ship skin renders to and link from
showmeSkinRendersChannel = 771368555019108352
# Resolution of skin render icons
skinRenderIconResolution = [600, 600]
skinRenderIconSamples = 8
# Resolution of skin render emojis (currently unused)
skinRenderEmojiResolution = [400, 400]
skinRenderEmojiSamples = 8
# Resolution of skin renders from cmd_showme_ship calls
skinRenderShowmeResolution = [352, 240]
skinRenderShowmeSamples = 4
# Resolution of skin renders from admin_cmd_showmeHD calls
skinRenderShowmeHDResolution = [1920, 1080]
skinRenderShowmeHDSamples = 4

# Default graphics to use for ship skin application tool items
defaultShipSkinToolIcon = "https://cdn.discordapp.com/attachments/700683544103747594/723472334362771536/documents.png"

# The maximum number of rendering threads that may be dispatched simultaneously
maxConcurrentRenders = 1

defaultCrateIcon = "https://cdn.discordapp.com/attachments/700683544103747594/723472359113359410/secure_container.png" 



##### ITEMS #####

# max number of characters accepted by nameShip
maxShipNickLength = 30

# max number of characters accepted by nameShip, when called by a developer
maxDevShipNickLength = 100

# The maximum number of items that will be displayed per page of a user's hangar, when all item types are requested
maxItemsPerHangarPageAll = 3
# The maximum number of items that will be displayed per page of a user's hangar, when a single item type is requested
maxItemsPerHangarPageIndividual = 10

# Names to be used when checking input to cmd_hangar and BasedUser.numInventoryPages
validItemNames = ["ship", "weapon", "module", "turret", "all", "tool"]

# the max number of each module type that can be equipped on a ship.
maxModuleTypeEquips = {     "ArmourModule": 1,
                            "BoosterModule": 1,
                            "CabinModule": -1,
                            "CloakModule": 1,
                            "CompressorModule": -1,
                            "GammaShieldModule": 1,
                            "MiningDrillModule": 1,
                            "RepairBeamModule": 1,
                            "RepairBotModule": 1,
                            "ScannerModule": 1,
                            "ShieldModule": 1,
                            "SpectralFilterModule": 1,
                            "ThrusterModule": 1,
                            "TractorBeamModule": 1,
                            "TransfusionBeamModule": 1,
                            "WeaponModModule": 1,
                            "JumpDriveModule": 0,
                            "EmergencySystemModule": 1,
                            "SignatureModule": 1,
                            "ShieldInjectorModule": 1,
                            "TimeExtenderModule": 1}

# valid types of crateItem that are in the game. Each will be associated with a zero-indexed (crateNum) list of crate objects
crateTypes = ("levelUp", "special")



##### MISC #####

# Exactly one of botToken or botToken_envVarName must be given.
# botToken contains a string of your bot token
# botToken_envVarName contains the name of an environment variable to get your bot token from
botToken = ""
botToken_envVarName = ""

# The number of times to retry API calls when HTTP exceptions are thrown
httpErrRetries = 3

# The number of seconds to wait between API call retries upon HTTP exception catching
httpErrRetryDelaySeconds = 1

# The categories to sort and save logs into
loggingCategories = [   "usersDB", "guildsDB", "bountiesDB", "shop", "escapedBounties", "bountyConfig", "duels", "hangar",
                        "bountyBoards", "newBounties", "reactionMenus", "userAlerts"]

# The maximum recursion depth of directory-walking when loading gameObjects from their JSON representation
gameObjectCfgMaxRecursion = 6
