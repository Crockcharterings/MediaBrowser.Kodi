import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import httplib
import requests
import hashlib
import StringIO
import gzip
import sys
import json as json
from uuid import getnode as get_mac
from ClientInformation import ClientInformation

class DownloadUtils():

    logLevel = 0
    addonSettings = None
    getString = None
   
    def __init__(self, *args):
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        self.getString = self.addonSettings.getLocalizedString
        level = self.addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)

    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C DownloadUtils -> " + msg)

    def getUserId(self):

        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        userName = self.addonSettings.getSetting('username')
        
        self.logMsg("Looking for user name: " + userName)

        jsonData = None
        try:
            jsonData = self.downloadUrl(host + ":" + port + "/mediabrowser/Users?format=json")
        except Exception, msg:
            error = "Get User unable to connect to " + host + ":" + port + " : " + str(msg)
            xbmc.log (error)
            return ""
        
        
        self.logMsg("GETUSER_JSONDATA_01:" + str(jsonData))
            
        result = []
        
        try:
            result = json.loads(jsonData)
        except Exception, e:
            self.logMsg("jsonload : " + str(e) + " (" + jsonData + ")", level=1)
            return ""           
        
        self.logMsg("GETUSER_JSONDATA_02:" + str(result))
        
        userid = ""
        secure = False
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")
                self.logMsg("Username Found:" + user.get("Name"))
                if(user.get("HasPassword") == True):
                    secure = True
                    self.logMsg("Username Is Secure (HasPassword=True)")
                break
                
        if(secure):
            self.authenticate('http://' + host + ":" + port + "/mediabrowser/Users/AuthenticateByName")
            
        if userid == "":
            return_value = xbmcgui.Dialog().ok(__language__(30045),__language__(30045))
            sys.exit()
            
        self.logMsg("userid : " + userid)
        
        WINDOW = xbmcgui.Window( 10000 )
        WINDOW.setProperty("userid", userid)
        
        return userid            
            
    def getMachineId(self):
        return "%012X"%get_mac()
    
    def authenticate(self, url):
        txt_mac = self.getMachineId()
        version = ClientInformation().getVersion()
        
        deviceName = self.addonSettings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")
            
        authString = "Mediabrowser Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
        headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}    
        sha1 = hashlib.sha1(self.addonSettings.getSetting('password'))
        resp = requests.post(url, data={'password':sha1.hexdigest(),'Username':self.addonSettings.getSetting('username')}, headers=headers)
        code=str(resp).split('[')[1]
        code=code.split(']')[0]
        if int(code) >= 200 and int(code)<300:
            self.logMsg("User Authenticated")
        else:
            self.logMsg("User NOT Authenticated")
            return_value = xbmcgui.Dialog().ok(self.getString(30044), self.getString(30044))
            sys.exit()            
            
    def getArtwork(self, data, type):
        
        id = data.get("Id")
        if type == "tvshow.poster": # Change the Id to the series to get the overall series poster
            if data.get("Type") == "Season" or data.get("Type")== "Episode":
                id = data.get("SeriesId")
        elif type == "poster" and data.get("Type") == "Episode" and self.addonSettings.getSetting('useSeasonPoster')=='true': # Change the Id to the Season to get the season poster
            id = data.get("SeasonId")
        if type == "poster" or type == "tvshow.poster": # Now that the Ids are right, change type to MB3 name
            type="Primary"
        if data.get("Type") == "Season":  # For seasons: primary (poster), thumb and banner get season art, rest series art
            if type != "Primary" and type != "Thumb" and type != "Banner":
                id = data.get("SeriesId")
        if data.get("Type") == "Episode":  # For episodes: primary (episode thumb) gets episode art, rest series art. 
            if type != "Primary":
                id = data.get("SeriesId")
        imageTag = ""
        if(data.get("ImageTags") != None and data.get("ImageTags").get(type) != None):
            imageTag = data.get("ImageTags").get(type)   
                
        # use the local image proxy server that is made available by this addons service
        artwork = "http://localhost:15001/?id=" + str(id) + "&type=" + type + "&tag=" + imageTag
        self.logMsg("getArtwork : " + artwork, level=2)
        if type=="Primary" and imageTag=="":
            artwork=''
        return artwork            
            
    def downloadUrl(self, url, suppress=False, type="GET", popup=0 ):
        self.logMsg("== ENTER: getURL ==")
        try:
            if url[0:4] == "http":
                serversplit=2
                urlsplit=3
            else:
                serversplit=0
                urlsplit=1

            server=url.split('/')[serversplit]
            urlPath="/"+"/".join(url.split('/')[urlsplit:])

            self.logMsg("url = " + url)
            self.logMsg("server = "+str(server), level=2)
            self.logMsg("urlPath = "+str(urlPath), level=2)
            conn = httplib.HTTPConnection(server, timeout=20)
            #head = {"Accept-Encoding" : "gzip,deflate", "Accept-Charset" : "UTF-8,*"} 
            head = {"Accept-Encoding" : "gzip", "Accept-Charset" : "UTF-8,*"} 
            #head = getAuthHeader()
            conn.request(method=type, url=urlPath, headers=head)
            #conn.request(method=type, url=urlPath)
            data = conn.getresponse()
            self.logMsg("GET URL HEADERS : " + str(data.getheaders()), level=2)
            link = ""
            contentType = "none"
            if int(data.status) == 200:
                retData = data.read()
                contentType = data.getheader('content-encoding')
                self.logMsg("Data Len Before : " + str(len(retData)))
                if(contentType == "gzip"):
                    retData = StringIO.StringIO(retData)
                    gzipper = gzip.GzipFile(fileobj=retData)
                    link = gzipper.read()
                else:
                    link = retData
                    
                self.logMsg("Data Len After : " + str(len(link)))
                self.logMsg("====== 200 returned =======")
                self.logMsg("Content-Type : " + str(contentType))
                self.logMsg(link)
                self.logMsg("====== 200 finished ======")

            elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
                try: conn.close()
                except: pass
                return data.getheader('Location')

            elif int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                xbmc.log (error)
                if suppress is False:
                    if popup == 0:
                        xbmc.executebuiltin("XBMC.Notification(URL error: "+ str(data.reason) +",)")
                    else:
                        xbmcgui.Dialog().ok("Error",server)
                xbmc.log (error)
                try: conn.close()
                except: pass
                return ""
            else:
                link = ""
        except Exception, msg:
            error = "Unable to connect to " + str(server) + " : " + str(msg)
            xbmc.log (error)
            xbmc.executebuiltin("XBMC.Notification(\"XBMB3C\": URL error: Unable to connect to server,)")
            xbmcgui.Dialog().ok("","Unable to connect to host")
            #if suppress is False:
            #    if popup == 0:
            #        xbmc.executebuiltin("XBMC.Notification(\"XBMB3C\": URL error: Unable to connect to server,)")
            #    else:
            #        xbmcgui.Dialog().ok("","Unable to connect to host")
            raise
        else:
            try: conn.close()
            except: pass

        return link