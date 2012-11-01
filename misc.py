import os
import shutil
import sh

def createFilename(delta=0):
    timestamp = sh.date("--iso-8601=seconds", date="%s seconds" % delta).stdout.strip()
    return "yousee-epg_%s.xml" % timestamp

def rotateLogs(config):
    rotateEnabled = config.logFileMaxSize >= 0 and config.oldLogFiles > 0
    currentLogFull = os.path.exists(config.logFile) and os.path.getsize(config.logFile) > config.logFileMaxSize

    if rotateEnabled and currentLogFull:
        def numToFile(i): return "%s.%i" % (config.logFile, i)

        a = map(numToFile, range(0, config.oldLogFiles-1))
        b = map(numToFile, range(1, config.oldLogFiles))
        filePairs = filter(lambda (x,y): os.path.exists(x), zip(a,b))
        filePairs.reverse()

        for source, target in filePairs:
            print source, target
            shutil.move(source, target)

        shutil.move(config.logFile, "%s.0" % config.logFile)
        return True
    else:
        return False
