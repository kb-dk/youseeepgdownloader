import datetime
import json

class EpgConfig:
    def __init__(self, confPath):
        """Load file from confPath, and parse as json."""
        config = json.load(open(confPath))

        for key in ["Username", "Password", "DataDir", "TrashDir", "LogFile", "StateMonitor", "EpgAgeLimit", "EpgAgeLimitWiggleRoom", "EpgMinSize", "EpgMaxSize"]:
            if not config.has_key(key):
                raise Exception("Bad configuration: Missing \"%s\"." % key)

        self.username = config["Username"]
        self.password = config["Password"]
        self.epgUrl = config["EpgUrl"]
        self.dataDir = config["DataDir"]
        self.trashDir = config["TrashDir"]
        self.logFile = config["LogFile"]
        self.stateMonitor = config["StateMonitor"]
        self.epgAgeLimit = datetime.timedelta(hours=config["EpgAgeLimit"])
        self.epgAgeLimitWiggleRoom = datetime.timedelta(hours=config["EpgAgeLimitWiggleRoom"])
        self.epgMinSize = config["EpgMinSize"]
        self.epgMaxSize = config["EpgMaxSize"]
