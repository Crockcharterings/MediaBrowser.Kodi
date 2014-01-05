﻿import xbmc, xbmcgui, xbmcaddon, urllib, httplib, os, time, requests
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ) 

sDto='{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Dto}'
sEntities='{http://schemas.datacontract.org/2004/07/MediaBrowser.Model.Entities}'
sArrays='{http://schemas.microsoft.com/2003/10/Serialization/Arrays}'

#################################################################################################
# http image proxy server 
# This acts as a HTTP Image proxy server for all thumbs and artwork requests
# this is needed due to the fact XBMC can not use the MB3 API as it has issues with the HTTP response format
# this proxy handles all the requests and allows XBMC to call the MB3 server
#################################################################################################

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import os
import mimetypes
from threading import Thread
from SocketServer import ThreadingMixIn
from urlparse import parse_qs
from urllib import urlretrieve

class MyHandler(BaseHTTPRequestHandler):
    addonDataPath = ""
    mb3Host = ""
    mb3Port = 0
    debugLogging = "false"
    
    def logMsg(self, msg):
        if(self.debugLogging == "true"):
            xbmc.log("XBMB3C Image Proxy -> " + msg)
    
    def do_GET(self):
        params = parse_qs(self.path[2:])
        self.logMsg("Params : " + str(params))
        itemId = params["id"][0]
        requestType = params["type"][0]
        
        imageType = "Primary"
        if(requestType == "b"):
            imageType = "Backdrop"        
            
        remoteUrl = "http://" + self.mb3Host + ":" + self.mb3Port + "/mediabrowser/Items/" + itemId + "/Images/" + imageType + "?Format=png"
        localTempImage = self.addonDataPath + imageType + "_" + itemId + ".png"
        
        self.logMsg("Addon Data Path : " + self.addonDataPath)
        self.logMsg("MB3 Host : " + self.mb3Host)
        self.logMsg("MB3 Port : " + self.mb3Port)
        self.logMsg("Item ID : " + itemId)
        self.logMsg("Request Type : " + requestType)
        self.logMsg("Remote URL : " + remoteUrl)
        self.logMsg("Local Image Path : " + localTempImage)
        
        # get the remote image
        self.logMsg("Downloading Image")
        urlretrieve(remoteUrl, localTempImage)
        
        datestring = time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        length = os.path.getsize(localTempImage)
        
        self.logMsg("ReSending Image")
        f = open(localTempImage, 'rb')
        self.send_response(200)
        self.send_header('Content-type', 'image/png')
        self.send_header('Content-Length', length)
        self.send_header('Last-Modified', datestring)        
        self.end_headers()
        self.wfile.write(f.read())
        f.close()
        self.logMsg("Image Sent")
        
        self.logMsg("Local Image Deleted")
        os.remove(localTempImage)
        
    def do_HEAD(self):
        datestring = time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.send_response(200)
        self.send_header('Content-type', 'image/png')
        self.send_header('Last-Modified', datestring)
        self.end_headers()        
        
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def startServer():
    MyHandler.addonDataPath = __addondir__
    MyHandler.mb3Host = __settings__.getSetting('ipaddress')
    MyHandler.mb3Port =__settings__.getSetting('port')
    MyHandler.debugLogging = __settings__.getSetting('debug')
    server = ThreadingHTTPServer(("",15001), MyHandler)
    server.serve_forever()
    
xbmc.log("XBMB3s -> HTTP Image Proxy Server Starting")
Thread(target=startServer).start()
xbmc.log("XBMB3s -> HTTP Image Proxy Server NOW SERVING IMAGES")

#################################################################################################
# end http image proxy server 
#################################################################################################

sys.path.append(BASE_RESOURCE_PATH)
playTime=0
def markWatched (url):
    headers={'Accept-encoding': 'gzip','Authorization' : 'MediaBrowser', 'Client' : 'Dashboard', 'Device' : "Chrome 31.0.1650.57", 'DeviceId' : "f50543a4c8e58e4b4fbb2a2bcee3b50535e1915e", 'Version':"3.0.5070.20258", 'UserId':"ff"}
    resp = requests.post(url, data='', headers=headers)

def setPosition (url,method):
    WINDOW = xbmcgui.Window( 10000 )
    userid=WINDOW.getProperty("userid")
    authString='MediaBrowser UserId=\"' + userid + '\",Client=\"XBMC\",Device=\"XBMB3C\",DeviceId=\"42\",Version=\"0.6.5\"'
    headers={'Accept-encoding': 'gzip','Authorization' : authString}
    xbmc.log('Setting position via: ' + url)
    if method=='POST':
        resp = requests.post(url, data='', headers=headers)
    elif method=='DELETE':
        resp = requests.delete(url, data='', headers=headers)
    
class Service( xbmc.Player ):

    def __init__( self, *args ):
        xbmc.log("starting monitor service")
        pass

    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
        WINDOW = xbmcgui.Window( 10000 )
        if WINDOW.getProperty("watchedurl")!="":
            positionurl=WINDOW.getProperty("positionurl")
            setPosition(positionurl + '/Progress?PositionTicks=0','POST')

    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        WINDOW = xbmcgui.Window( 10000 )
        if WINDOW.getProperty("watchedurl")!="":
            watchedurl=WINDOW.getProperty("watchedurl")
            positionurl=WINDOW.getProperty("positionurl")
            setPosition(positionurl +'?PositionTicks=' + str(int(playTime*10000000)),'DELETE')
            xbmc.log ("runtimeticks:" + WINDOW.getProperty("runtimeticks"))
            percentComplete=(playTime*10000000)/int(WINDOW.getProperty("runtimeticks"))
            xbmc.log ("Percent complete:" + str(percentComplete))
            if ((playTime*10000000)/(int(WINDOW.getProperty("runtimeticks")))) > 0.95:
                markWatched(watchedurl)
            WINDOW.setProperty("watchedurl","")
            WINDOW.setProperty("positionurl","")
            WINDOW.setProperty("runtimeticks","")
            xbmc.log("stopped at time:" + str(playTime))

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        WINDOW = xbmcgui.Window( 10000 )
        if WINDOW.getProperty("watchedurl")!="":
            watchedurl=WINDOW.getProperty("watchedurl")
            positionurl=WINDOW.getProperty("positionurl")
            setPosition(positionurl +'?PositionTicks=' + str(int(playTime*10000000)),'DELETE')
            xbmc.log ("runtimeticks:" + WINDOW.getProperty("runtimeticks"))
            percentComplete=(playTime*10000000)/int(WINDOW.getProperty("runtimeticks"))
            xbmc.log ("Percent complete:" + str(percentComplete))
            if ((playTime*10000000)/(int(WINDOW.getProperty("runtimeticks")))) > 0.95:
                markWatched(watchedurl)
            WINDOW.setProperty("watchedurl","")
            WINDOW.setProperty("positionurl","")
            WINDOW.setProperty("runtimeticks","")
            xbmc.log("stopped at time:" + str(playTime))

montior=Service()        
while not xbmc.abortRequested:
    if xbmc.Player().isPlaying():
        try:
            playTime=xbmc.Player().getTime()
        except:
            pass
        xbmc.sleep(100)
    else:
        xbmc.sleep(1000)
    
xbmc.log("Service shutting down")