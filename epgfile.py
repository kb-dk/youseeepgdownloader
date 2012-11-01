import datetime
import hashlib
import logging
import os
import shutil
import sh

class EpgFile():
    def __init__(self, config, path, data=None):
        self.config = config
        self.path = path
        self.data = data


    def _getContent(self):
        if self.data:
            return self.data
        else:
            with open(self.path) as f:
                return f.read()


    def getPath(self):
        return self.path


    def getSize(self):
        return len(self._getContent())


    def getPrettySize(self):
        return round(float(self.getSize())/1024/1024, 1)


    def getMd5sum(self):
        """Calculate the md5sum for the newest EPG file."""
        m = hashlib.md5()
        m.update(self._getContent())
        return m.hexdigest()


    def getTimeOfLastModification(self):
        """Get hours since last modification."""
        modTime = os.path.getmtime(self.path)
        return datetime.datetime.fromtimestamp(modTime)


    def getAge(self):
        """Calculate the age of this EPG file."""
        return datetime.datetime.today() - self.getTimeOfLastModification()


    def isValidXml(self):
        """Use xmllint to check the file for well-formed ness."""
        try:
            sh.xmllint("--noout", self.path)
        except sh.ErrorReturnCode_1:
            return False
        else:
            return True


    def fileSizeOK(self):
        """Check whether the size of data is of a expected size."""
        return self.config.epgMinSize < self.getSize() < self.config.epgMaxSize


    def persist(self):
        """Decide whether or not to saved the downloaded EPG data.
         If the md5sum is the same as the previous, the new data is thrown away,
         otherwise it is saved.
         """

        if self.data:
            with open(self.path, "w") as f:
                f.write(self.data)

            return True
        else:
            return False


    def moveToTrash(self):
        if not os.path.exists(self.config.trashDir):
            os.mkdir(self.config.trashDir)

        elif not os.path.isdir(self.config.trashDir):
            logging.critical("Could not move data to trash, \"%s\" is not a directory.")
            return False

        target = os.path.join(self.config.trashDir, os.path.basename(self.path))

        if os.path.exists(target):
            logging.error("Tried to trash a file, but \"%s\" already exists." % target)
            return False

        shutil.move(self.path, target)
        return target
