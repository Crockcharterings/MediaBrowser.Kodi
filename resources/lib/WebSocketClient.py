#################################################################################################
# WebSocket Client thread
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
import urllib
import websocket
from ClientInformation import ClientInformation

_MODE_BASICPLAY=12

class WebSocketThread(threading.Thread):

    logLevel = 0
    client = None
    keepRunning = True
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("XBMB3C WebSocketThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C WebSocketThread -> " + msg)    
    
    def playbackStarted(self, itemId):
        if(self.client != None):
            try:
                self.logMsg("Sending Playback Started")
                messageData = {}
                messageData["MessageType"] = "PlaybackStart"
                messageData["Data"] = itemId + "|true|audio,video"
                messageString = json.dumps(messageData)
                self.logMsg("Message Data : " + messageString)
                self.client.send(messageString)
            except Exception, e:
                self.logMsg("Exception : " + str(e), level=0)
        else:
            self.logMsg("Sending Playback Started NO Object ERROR")
            
    def playbackStopped(self, itemId, ticks):
        if(self.client != None):
            try:
                self.logMsg("Sending Playback Stopped")
                messageData = {}
                messageData["MessageType"] = "PlaybackStopped"
                messageData["Data"] = itemId + "|" + str(ticks)
                messageString = json.dumps(messageData)
                self.client.send(messageString)
            except Exception, e:
                self.logMsg("Exception : " + str(e), level=0)            
        else:
            self.logMsg("Sending Playback Stopped NO Object ERROR")
            
    def sendProgressUpdate(self, itemId, ticks):
        if(self.client != None):
            try:
                self.logMsg("Sending Progress Update")
                messageData = {}
                messageData["MessageType"] = "PlaybackProgress"
                messageData["Data"] = itemId + "|" + str(ticks) + "|false|false"
                messageString = json.dumps(messageData)
                self.logMsg("Message Data : " + messageString)
                self.client.send(messageString)
            except Exception, e:
                self.logMsg("Exception : " + str(e), level=0)              
        else:
            self.logMsg("Sending Progress Update NO Object ERROR")
            
    def stopClient(self):
        # stopping the client is tricky, first set keep_running to false and then trigger one 
        # more message by requesting one SessionsStart message, this causes the 
        # client to receive the message and then exit
        if(self.client != None):
            try:
                self.logMsg("Stopping Client")
                self.keepRunning = False
                self.client.keep_running = False
                messageData = {}
                messageData["MessageType"] = "SessionsStart"
                messageData["Data"] = "300,0"
                messageString = json.dumps(messageData)
                self.client.send(messageString)
            except Exception, e:
                self.logMsg("Exception : " + str(e), level=0)              
        else:
            self.logMsg("Stopping Client NO Object ERROR")
            
    def on_message(self, ws, message):
        self.logMsg("Message : " + str(message))
        result = json.loads(message)
        
        messageType = result.get("MessageType")
        playCommand = result.get("PlayCommand")
        data = result.get("Data")
        
        if(messageType != None and messageType == "Play" and data != None):
            itemIds = data.get("ItemIds")
            playCommand = data.get("PlayCommand")
            if(playCommand != None and playCommand == "PlayNow"):
            
                startPositionTicks = data.get("StartPositionTicks")
                self.logMsg("Playing Media With ID : " + itemIds[0])
                
                addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
                mb3Host = addonSettings.getSetting('ipaddress')
                mb3Port = addonSettings.getSetting('port')                   
                
                url =  mb3Host + ":" + mb3Port + ',;' + itemIds[0]
                if(startPositionTicks == None):
                    url  += ",;" + "-1"
                else:
                    url  += ",;" + str(startPositionTicks)
                    
                playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
                playUrl = playUrl.replace("\\\\","smb://")
                playUrl = playUrl.replace("\\","/")                
                
                xbmc.Player().play(playUrl)
                
        elif(messageType != None and messageType == "Playstate"):
            command = data.get("Command")
            if(command != None and command == "Stop"):
                self.logMsg("Playback Stopped")
                xbmc.executebuiltin('xbmc.activatewindow(10000)')
                xbmc.Player().stop()
                
            if(command != None and command == "Seek"):
                seekPositionTicks = data.get("SeekPositionTicks")
                self.logMsg("Playback Seek : " + str(seekPositionTicks))
                seekTime = (seekPositionTicks / 1000) / 10000
                xbmc.Player().seekTime(seekTime)

    def on_error(self, ws, error):
        self.logMsg("Error : " + str(error))

    def on_close(self, ws):
        self.logMsg("Closed")

    def on_open(self, ws):
        try:
            clientInfo = ClientInformation()
            machineId = clientInfo.getMachineId()
            version = clientInfo.getVersion()
            messageData = {}
            messageData["MessageType"] = "Identity"
            
            addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
            deviceName = addonSettings.getSetting('deviceName')
            deviceName = deviceName.replace("\"", "_")
        
            messageData["Data"] = "XBMC|" + machineId + "|" + version + "|" + deviceName
            messageString = json.dumps(messageData)
            self.logMsg("Opened : " + str(messageString))
            ws.send(messageString)
        except Exception, e:
            self.logMsg("Exception : " + str(e), level=0)                
        
    def getWebSocketPort(self, host, port):
        
        userUrl = "http://" + host + ":" + port + "/mediabrowser/System/Info?format=json"
        
        try:
            requesthandle = urllib.urlopen(userUrl, proxies={})
            jsonData = requesthandle.read()
            requesthandle.close()              
        except Exception, e:
            self.logMsg("WebSocketThread getWebSocketPort urlopen : " + str(e) + " (" + userUrl + ")", level=0)
            return -1

        result = json.loads(jsonData)     

        wsPort = result.get("WebSocketPortNumber")
        if(wsPort != None):
            return wsPort
        else:
            return -1

    def run(self):
    
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')
        
        if(self.logLevel >= 1):
            websocket.enableTrace(True)        

        wsPort = self.getWebSocketPort(mb3Host, mb3Port);
        self.logMsg("WebSocketPortNumber = " + str(wsPort))
        if(wsPort == -1):
            self.logMsg("Could not retrieve WebSocket port, can not run WebScoket Client")
            return
        
        # Make a call to /System/Info. WebSocketPortNumber is the port hosting the web socket.
        webSocketUrl = "ws://" +  mb3Host + ":" + str(wsPort) + "/mediabrowser"
        self.logMsg("WebSocket URL : " + webSocketUrl)
        self.client = websocket.WebSocketApp(webSocketUrl,
                                    on_message = self.on_message,
                                    on_error = self.on_error,
                                    on_close = self.on_close)
                                    
        self.client.on_open = self.on_open
        
        while(self.keepRunning):
            self.logMsg("Client Starting")
            self.client.run_forever()
            if(self.keepRunning):
                self.logMsg("Client Needs To Restart")
                xbmc.sleep(10000)
            
        self.logMsg("Thread Exited")
        
        
        
        