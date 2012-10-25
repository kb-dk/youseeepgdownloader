from httplib import HTTPConnection
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

        connection = HTTPConnection(address)

        connection.request("POST", path, data, {"Content-Type": "text/xml", "Accept": "application/json"})
        response = connection.getresponse()

        self.response = response.read()

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
