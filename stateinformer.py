from httplib import HTTPConnection
from urllib import quote
from urlparse import urlparse

class StateInformer():
    def __init__(self, entity, stateMonitorAddress):
        self.response = None
        self.entity = entity
        self.stateMonitorAddress = stateMonitorAddress

    def getAddress(self):
        urlParts = urlparse(self.stateMonitorAddress)
        address = urlParts.netloc
        path =  urlParts.path + "/states/" + quote(self.entity)
        return address, path

    def createPayload(self, component, state, message=""):
        component = "<component>%s</component>" % component
        state = "<stateName>%s</stateName>" % state

        if message is not "":
            message = "<message><![CDATA[%s]]></message>" % message

        return "<state>%s%s%s</state>" % (component, state, message)

    def postStatus(self, component, state, message=""):
        print self.entity, component, state + ":", message

        data = self.createPayload(component, state, message)
        (address, path) = self.getAddress()

        connection = HTTPConnection(address)


        connection.request("POST", path, data, {"Content-Type": "text/xml", "Accept": "application/json"})
        response = connection.getresponse()

        self.response = response.read()

        return response.status == 200

    def getResponse(self):
        return self.response
