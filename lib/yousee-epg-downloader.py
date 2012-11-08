#!/usr/bin/env python

from __future__ import division

import os, sys, datetime, logging
import sh
from epgconfig import EpgConfig
from epgfile import EpgFile
from misc import rotateLogs, createFilename
from stateinformer import StateInformer

# defines
epgComponent = "yousee-epg-fetcher"
epgAgeCheck = "yousee-epg-age-check"
epgDownload = "yousee-epg-downloader"
epgSize = "yousee-epg-file-check"
epgMd5 = "yousee-epg-md5-check"
epgWriter = "yousee-epg-filewriter"
epgXml = "yousee-epg-xml-validator"

class YouseeEpgDownloader():
    def __init__(self, config, informer, filename):
        self.config = config
        self.filename = filename
        self.informer = informer


    def getInformerComponent(self):
        return informer.get(epgComponent)


    def fetchEpg(self, filename):
        """Use wget to fetch EPG data into memory"""
        try:
            wgetProc = sh.wget(self.config.epgUrl, "-nv", a=self.config.logFile, O="-", user=self.config.username, password=self.config.password)
        except sh.ErrorReturnCode:
            return None
        else:
            year = str(datetime.datetime.today().year)
            targetDir = os.path.join(self.config.dataDir, year)

            if not os.path.exists(targetDir):
                os.mkdir(targetDir)

            filepath = os.path.join(targetDir, filename)
            return EpgFile(self.config, filepath, data=wgetProc.stdout)


    def getNewestEpgFile(self):
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
                return EpgFile(self.config, os.path.join(thisDir, files[-1]))

        return None


    def saveNewEpgData(self, epg):
        """Decide whether or not to saved the downloaded EPG data.
         If the md5sum is the same as the previous, the new data is thrown away,
         otherwise it is saved.
         """
        oldEpg = self.getNewestEpgFile()
        new_md5sum = epg.getMd5sum()
        save = False

        if new_md5sum:
            if oldEpg:
                if oldEpg.getMd5sum() != new_md5sum:
                    save = True
            else:
                save = True

        if save:
            return epg.persist()
        else:
            return False


    def reportMissingEpgFiles(self, newestEpg):
        def missingEpgs():
            """Yield a list of seconds relative to now that corresponds to a time where epg should have been downloaded. Very roughly."""
            now = datetime.datetime.today()
            t = self.config.epgAgeLimit

            while now - t > newestEpg.getTimeOfLastModification():
                yield (t.microseconds + (t.seconds + t.days * 24 * 3600) * 10**6) / 10**6
                t += self.config.epgAgeLimit

        for epg in missingEpgs():
            filename_ = createFilename(-epg)
            informer_ = StateInformer(filename_, self.config.stateMonitor)
            epgComponent_ = informer_.get(epgComponent)
            epgComponent_.failed()
            msg = "Missing EPG: " + filename_
            logging.error(msg)


    def run(self):
        errors = 0
        msgs = []

        # age related checks
        epgAgeCheckComponent = informer.get(epgAgeCheck)
        epgAgeCheckComponent.started()
        newestEpg = self.getNewestEpgFile()

        if newestEpg:
            epgTooOld = newestEpg.getAge() > (self.config.epgAgeLimit + self.config.epgAgeLimitWiggleRoom)
        else:
            epgTooOld = False

        if epgTooOld:
            msg = "Last EPG is too old. Age: %s" % str(newestEpg.getAge())
            logging.error(msg)
            msgs.append(msg)
            self.reportMissingEpgFiles(newestEpg)


        epgAgeCheckComponent.completed()

        # download epg data into memory using wget
        epgDownloadComponent = informer.get(epgDownload)
        epgDownloadComponent.started()
        newEpg = self.fetchEpg(filename)

        if not newEpg:
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

        if not newEpg.fileSizeOK():
            msg = "EPG data seems to have an unexpected size. Expected ~6.5MB, was %sMB." % newEpg.getPrettySize()
            logging.error(msg)
            msgs.append(msg)
            epgSizeComponent.failed(msg)
            errors += 1
            return msgs, errors
        else:
            msg = "Filesize OK: %sMB" % newEpg.getPrettySize()
            logging.info(msg)
            msgs.append(msg)
            epgSizeComponent.completed(msg)

        # get the md5sum of the downloaded data
        epgMd5Component = informer.get(epgMd5)
        epgMd5Component.started()
        md5sum = newEpg.getMd5sum()

        if not md5sum:
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
        persisted = self.saveNewEpgData(newEpg)

        if persisted is None:
            msg = "Something unexpected happened while deciding whether or not to keep the new file."
            logging.error(msg)
            msgs.append(msg)
            epgWriterComponent.failed(msg)
            errors += 1
            return msgs, errors
        elif persisted is False:
            if epgTooOld:
                msg = "EPG haven't been updated in " + str(newestEpg.getAge())
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
            msg = "Saved EPG data to file: " + newEpg.getPath()
            logging.info(msg)
            msgs.append(msg)
            epgWriterComponent.completed(msg)

        # run xmllint on the downloaded data
        epgXmlComponent = informer.get(epgXml)
        epgXmlComponent.started()
        validXml = newEpg.isValidXml()

        if not validXml:
            trashPath = newEpg.moveToTrash()
            if trashPath:
                msg = "Invalid XML, moved to \"%s\"." % trashPath
            else:
                msg = "Invalid XML, but failed while moving the file to the trash."
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
        raise
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
            raise
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
