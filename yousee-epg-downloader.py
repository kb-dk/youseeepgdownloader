#!/usr/bin/env python

import os
import sys
import shutil
import datetime
import hashlib
import logging
from epgconfig import EpgConfig

import sh

from stateinformer import StateInformer


# defines

epgComponent = "yousee-epg-fetcher"
epgAgeCheck = "yousee-epg-age-check"
epgDownload = "yousee-epg-downloader"
epgSize = "yousee-epg-file-check"
epgMd5 = "yousee-epg-md5-check"
epgWriter = "yousee-epg-filewriter"
epgXml = "yousee-epg-xml-validator"


def createFilename(delta=0):
    timestamp = sh.date("--iso-8601=seconds", date="%s seconds" % delta).stdout.strip()
    return "yousee-epg_%s.xml" % timestamp


class YouseeEpgDownloader():
    def __init__(self, config, informer, filename):
        self.config = config
        self.filename = filename
        self.informer = informer


    def getInformerComponent(self):
        return informer.get(epgComponent)


    def fetchEpg(self):
        """Use wget to fetch EPG data into memory"""
        try:
            wgetProc = sh.wget(self.config.epgUrl, "-nv", a=self.config.logFile, O="-", user=self.config.username, password=self.config.password)
        except sh.ErrorReturnCode:
            return None
        else:
            return wgetProc.stdout


    def fileSizeOK(self, data):
        """Check whether the size of data is of a expected size."""
        return self.config.epgMinSize < len(data) < self.config.epgMaxSize


    def validXmlFile(self, path):
        """Use xmllint to check the file for well-formed ness."""
        try:
            sh.xmllint("--noout", path)
        except sh.ErrorReturnCode_1:
            return False
        else:
            return True


    def timeOfLastModification(self, path):
        """Get hours since the last modification of path."""
        if not os.path.exists(path):
            return None

        modTime = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(modTime)


    def getMd5sum(self, data):
        """Calculate a md5sum for data."""
        m = hashlib.md5()
        m.update(data)
        return m.hexdigest()


    def getLatestEpgFilePath(self):
        """Get the newest EPG file stored in the data directory."""

        # get the files and dirs in self.config.dataDir
        dirs = sorted(os.listdir(self.config.dataDir))

        # directories are supposed to be named like "2012", "2013", ..;
        # - remove elements where the filename has a length different from 4,
        # - and isn't a number.
        dirs = filter(lambda thisDir: len(thisDir) == 4 and thisDir.isdigit(), dirs)

        # turn the dirnames into paths relative to self.config.dataDir
        dirs = map(lambda dir: os.path.join(self.config.dataDir, dir), dirs)

        # filter out non-directories, and reverse the list so that the newest will be first.
        dirs = filter(os.path.isdir, dirs)
        dirs.reverse()

        for thisDir in dirs:
            files = sorted(os.listdir(thisDir))
            if len(files) != 0:
                return os.path.join(thisDir, files[-1])

        return None


    def getLatestMd5Sum(self):
        """Calculate the md5sum for the latest EPG file."""
        latestEpg = self.getLatestEpgFilePath()
        if latestEpg is None:
            return None
        else:
            f = open(latestEpg)
            return self.getMd5sum(f.read())


    def getAgeOfLatestEpgFile(self):
        """Calculate the age of the latest EPG file."""
        latestEpg = self.getLatestEpgFilePath()
        if latestEpg is None:
            return None
        else:
            return datetime.datetime.today() - self.timeOfLastModification(latestEpg)


    def getMTimeOfLatestEpgFile(self):
        """Calculate the age of the latest EPG file."""
        latestEpg = self.getLatestEpgFilePath()
        if latestEpg is None:
            return None
        else:
            return self.timeOfLastModification(latestEpg)


    def saveNewEpgData(self, data, filename):
        """Decide whether or not to saved the downloaded EPG data.
         If the md5sum is the same as the previous, the new data is thrown away,
         otherwise it is saved.
         """

        year = str(datetime.datetime.today().year)
        targetDir = os.path.join(config.dataDir, year)

        if not os.path.exists(targetDir):
            os.mkdir(targetDir)

        filepath = os.path.join(targetDir, filename)
        old_md5sum = self.getLatestMd5Sum()
        new_md5sum = self.getMd5sum(data)

        if old_md5sum is None and new_md5sum is None:
            return None
        elif old_md5sum != new_md5sum:
            if not os.path.exists(filepath):
                f = open(filepath, "w")
                f.write(data)
                f.close()
                return filepath
            else:
                return False
        else:
            return False


    def moveToTrash(self, src):
        if not os.path.exists(config.trashDir):
            os.mkdir(config.trashDir)

        elif not os.path.isdir(config.trashDir):
            logging.critical("Could not move data to trash, \"%s\" is not a directory.")
            return False

        target = os.path.join(config.trashDir, os.path.basename(src))

        if os.path.exists(target):
            logging.error("Tried to trash a file, but \"%s\" already exists." % target)
            return False

        shutil.move(src, target)
        return target


    def convertByteToMB(self, numberOfByte):
        """Hack to convert a number of bytes into the MB-range."""
        return round(float(numberOfByte)/1024/1024, 1)


    def run(self):
        errors = 0
        msgs = []

        # age related checks
        epgAgeCheckComponent = informer.get(epgAgeCheck)
        epgAgeCheckComponent.started()
        lastEpgModification = self.getMTimeOfLatestEpgFile()

        if lastEpgModification is not None:
            ageOfLatestEpgFile = (datetime.datetime.today() - lastEpgModification)
            epgTooOld = ageOfLatestEpgFile > (self.config.epgAgeLimit + self.config.epgAgeLimitWiggleRoom)
        else:
            ageOfLatestEpgFile = None
            epgTooOld = False

        if epgTooOld:
            msg = "Last EPG is too old. Age: %s" % str(ageOfLatestEpgFile)
            logging.error(msg)
            msgs.append(msg)

            def missingEpgs():
                """Yield a list of seconds relative to now that corresponds to a time where epg should have been downloaded. Very roughly."""
                now = datetime.datetime.today()
                t = self.config.epgAgeLimit

                while now - t > lastEpgModification:
                    yield t.total_seconds()
                    t += self.config.epgAgeLimit

            for epg in missingEpgs():
                filename_ = createFilename(-epg)
                informer_ = StateInformer(filename_, self.config.stateMonitor)
                epgComponent_ = informer_.get(epgComponent)
                epgComponent_.failed()
                msg = "Missing EPG: " + filename_
                logging.error(msg)


        epgAgeCheckComponent.completed()

        # download epg data into memory using wget
        epgDownloadComponent = informer.get(epgDownload)
        epgDownloadComponent.started()
        newEpgData = self.fetchEpg()

        if not newEpgData:
            msg = "Failed to fetch EPG data."
            logging.error(msg)
            msgs.append(msg)
            epgDownloadComponent.failed(msg)
            errors += 1
            return msgs, errors
        else:
            msg = "Fetched EPG data."
            logging.info(msg)
            msgs.append(msg)
            epgDownloadComponent.completed(msg)

        # check size of the downloaded data
        epgSizeComponent = informer.get(epgSize)
        epgSizeComponent.started()
        prettyFileSize = self.convertByteToMB(len(newEpgData))

        if not self.fileSizeOK(newEpgData):
            msg = "EPG data seems to have an unexpected size. Expected ~6.5MB, was %sMB." % prettyFileSize
            logging.error(msg)
            msgs.append(msg)
            epgSizeComponent.failed(msg)
            errors += 1
            return msgs, errors
        else:
            msg = "Filesize OK: %sMB" % prettyFileSize
            logging.info(msg)
            msgs.append(msg)
            epgSizeComponent.completed(msg)

        # get the md5sum of the downloaded data
        epgMd5Component = informer.get(epgMd5)
        epgMd5Component.started()
        md5sum = self.getMd5sum(newEpgData)

        if md5sum is None:
            msg = "Failed to get md5sum for downloaded data."
            logging.error(msg)
            msgs.append(msg)
            epgMd5Component.failed(msg)
            errors += 1
            return msgs, errors
        else:
            msg = "md5sum: " + md5sum
            logging.info(msg)
            msgs.append(msg)
            epgMd5Component.completed(msg)

        # persist the downloaded data to disk
        epgWriterComponent = informer.get(epgWriter)
        epgWriterComponent.started()
        path = self.saveNewEpgData(newEpgData, filename)

        if path is None:
            msg = "Something unexpected happened while deciding whether or not to keep the new file."
            logging.error(msg)
            msgs.append(msg)
            epgWriterComponent.failed(msg)
            errors += 1
            return msgs, errors
        elif path is False:
            if epgTooOld:
                msg = "EPG haven't been updated in " + str(ageOfLatestEpgFile)
                logging.error(msg)
                msgs.append(msg)
                errors += 1
                epgWriterComponent.failed(msg)
                return msgs, errors
            else:
                msg = "Unchanged EPG data, didn't save."
                logging.info(msg)
                msgs.append(msg)
                epgWriterComponent.completed(msg)
                return msgs, errors
        else:
            msg = "Saved EPG data to file: " + path
            logging.info(msg)
            msgs.append(msg)
            epgWriterComponent.completed(msg)

        # run xmllint on the downloaded data
        epgXmlComponent = informer.get(epgXml)
        epgXmlComponent.started()
        validXml = self.validXmlFile(path)

        if not validXml:
            trashPath = self.moveToTrash(path)
            msg = "Invalid XML, moved to \"%s\"." % trashPath
            logging.error(msg)
            msgs.append(msg)
            epgXmlComponent.failed(msg)
            errors += 1
        else:
            msg = "Valid XML."
            logging.info(msg)
            msgs.append(msg)
            epgXmlComponent.completed(msg)

        return msgs, errors


def rotateLogs(config):
    if config.oldLogFiles > 0 and  os.path.exists(config.logFile) and os.path.getsize(config.logFile) > config.logFileMaxSize:
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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: %s config-file" % sys.argv[0]
        sys.exit(1)
    else:
        configFile = sys.argv[1]

    try:
        config = EpgConfig(configFile)
    except Exception as e:
        print "Error loading the config file: " + configFile
        print e.message
        sys.exit(2)
    else:
        rotateLogs(config)
        logging.basicConfig(filename=config.logFile,level=logging.INFO, format='%(asctime)s: %(message)s')
        filename = createFilename()
        informer = StateInformer(filename, config.stateMonitor)
        epgComponent_ = informer.get(epgComponent)
        try:
            downloader = YouseeEpgDownloader(config, informer, filename)
            logging.info("Created new %s for \"%s\", using \"%s\" as state monitor." % (downloader.__class__.__name__, filename, config.stateMonitor))
            epgComponent_.started()
            (messages, errors) = downloader.run()
        except Exception as e:
            epgComponent_.failed(e.message)
            logging.error("Failed: %s" % filename)
            print e.message
            sys.exit(3)
        else:
            if errors > 0:
                epgComponent_.failed("\n".join(messages))
                logging.error("Failed: %s" % filename)
                exitCode = 4
            else:
                epgComponent_.done()
                logging.info("Done: %s" % filename)
                exitCode = 0

            logging.shutdown()
            sys.exit(exitCode)