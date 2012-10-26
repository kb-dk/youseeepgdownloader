import datetime
import json

class EpgConfig:
    def __init__(self, confPath):
        """Load file from confPath, and parse as json."""
        config = json.load(open(confPath))

        for key in ["Username", "Password", "DataDir", "LogFile", "StateMonitor", "EpgAgeLimit", "EpgMinSize", "EpgMaxSize"]:
            if not config.has_key(key):
                raise Exception("Bad configuration: Missing \"%s\"." % key)

        self.username = config["Username"]
        self.password = config["Password"]
        self.epgUrl = config["EpgUrl"]
        self.dataDir = config["DataDir"]
        self.logFile = config["LogFile"]
        self.stateMonitor = config["StateMonitor"]
        self.epgAgeLimit = datetime.timedelta(hours=config["EpgAgeLimit"])
        self.epgMinSize = config["EpgMinSize"]
        self.epgMaxSize = config["EpgMaxSize"]
