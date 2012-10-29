import logging
from httplib import HTTPConnection
import socket
from urllib import quote
from urlparse import urlparse


class StateInformerComponent():
    stateStarted="Started"
    stateFailed="Failed"
    stateCompleted="Completed"
    stateDone="Done"

    def __init__(self, stateMonitorAddress, entity, component):
        self.stateMonitorAddress = stateMonitorAddress
        self.component = component
        self.entity = entity


    def getAddress(self):
        urlParts = urlparse(self.stateMonitorAddress)
        address = urlParts.netloc
        path =  urlParts.path + "/states/" + quote(self.entity)
        logging.debug("Created url: \"%s%s\"" % (address, path))
        return address, path


    def __createPayload(self, state, message=""):
        component = "<component>%s</component>" % self.component
        state = "<stateName>%s</stateName>" % state

        if message is not "":
            message = "<message><![CDATA[%s]]></message>" % message

        return "<state>%s%s%s</state>" % (component, state, message)


    def __postStatus(self, state, message=""):
        data = self.__createPayload(state, message)
        (address, path) = self.getAddress()

        errorMsg = "Failed to communicate with state monitor at %s" % self.stateMonitorAddress

        try:
            connection = HTTPConnection(address)
            logging.debug("Setting state for \"%s\" to \"%s\"" % (self.entity, state))
            connection.request("POST", path, data, {"Content-Type": "text/xml", "Accept": "application/json"})
            response = connection.getresponse()

            self.response = response.read()
        except socket.error as e:
            logging.error("%s: %s" % (errorMsg, e))
            return False
        else:
            if response.status != 200:
                logging.error("%s: %s %s%s" % (errorMsg, response.status, response.reason))

            return response.status == 200


    def getResponse(self):
        return self.response

    def started(self, message=""):
        return self.__postStatus(self.stateStarted, message)

    def failed(self, message=""):
        return self.__postStatus(self.stateFailed, message)

    def completed(self, message=""):
        return self.__postStatus(self.stateCompleted, message)

    def done(self, message=""):
        return self.__postStatus(self.stateDone, message)


class StateInformer():
    def __init__(self, entity, stateMonitorAddress):
        self.response = None
        self.entity = entity
        self.stateMonitorAddress = stateMonitorAddress


    def get(self, component):
        return StateInformerComponent(self.stateMonitorAddress, self.entity, component)
