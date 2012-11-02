import os
import shutil
import sh

def createFilename(delta=0):
    timestamp = sh.date("--iso-8601=seconds", date="%s seconds" % delta).stdout.strip()
    return "yousee-epg_%s.xml" % timestamp

def rotateLogs(config):
    """ Rotates the logs, when applicable.
    To rotate the logs, a list of tuples containing source and destination of files to
    move is generated.
    """
    rotateEnabled = config.logFileMaxSize >= 0 and config.oldLogFiles > 0
    currentLogFull = os.path.exists(config.logFile) and os.path.getsize(config.logFile) > config.logFileMaxSize

    if rotateEnabled and currentLogFull:
        def numToFile(i): return "%s.%i" % (config.logFile, i)

        # [log.0, log.1, .., log.(n-1)]
        a = map(numToFile, range(0, config.oldLogFiles-1))
        # [log.1, log.2, .., log.n]
        b = map(numToFile, range(1, config.oldLogFiles))
        # zip(a,b) creates a list of tuples: [(log.0, log.1), (log.1, log.2), .., (log.(n-1), log.n)],
        # and filter removes the tuples where the source file does not exist.
        filePairs = filter(lambda (x,y): os.path.exists(x), zip(a,b))
        # The list is reversed, so that .n is moved to .(n+1) before .(n-1) is moved to .n.
        # If the list isn't reversed, .0 would be copied to .1, then .1 to .2, which is
        # obviously bad.
        filePairs.reverse()
        filePairs.append((config.logFile, numToFile(0)))

        for source, target in filePairs:
            shutil.move(source, target)

        return True
    else:
        return False
