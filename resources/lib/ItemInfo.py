
import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from DownloadUtils import DownloadUtils

_MODE_BASICPLAY=12
_MODE_CAST_LIST=14
_MODE_PERSON_DETAILS=15

class ItemInfo(xbmcgui.WindowXMLDialog):

    id = ""
    playUrl = ""
    trailerUrl = ""
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        xbmc.log("WINDOW INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        port = __settings__.getSetting('port')
        host = __settings__.getSetting('ipaddress')
        server = host + ":" + port         
        
        downloadUtils = DownloadUtils()
        
        userid = downloadUtils.getUserId()
       
        jsonData = downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + self.id + "?format=json", suppress=False, popup=1 )     
        item = json.loads(jsonData)
        
        id = item.get("Id")
        name = item.get("Name")
        image = downloadUtils.getArtwork(item, "Primary3")
        fanArt = downloadUtils.getArtwork(item, "BackdropNoIndicators")
        
        # calculate the percentage complete
        userData = item.get("UserData")
        cappedPercentage = None
        if(userData != None):
            playBackTicks = float(userData.get("PlaybackPositionTicks"))
            if(playBackTicks != None and playBackTicks > 0):
                runTimeTicks = float(item.get("RunTimeTicks", "0"))
                if(runTimeTicks > 0):
                    percentage = int((playBackTicks / runTimeTicks) * 100.0)
                    cappedPercentage = percentage - (percentage % 10)
                    if(cappedPercentage == 0):
                        cappedPercentage = 10
                    if(cappedPercentage == 100):
                        cappedPercentage = 90        
        
        episodeInfo = ""
        type = item.get("Type")
        if(type == "Episode" or type == "Season"):
            name = item.get("SeriesName") + ": " + name
            season = str(item.get("ParentIndexNumber")).zfill(2)
            episodeNum = str(item.get("IndexNumber")).zfill(2)
            episodeInfo = "S" + season + "xE" + episodeNum
            
        url =  server + ',;' + id
        url = urllib.quote(url)
        self.playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            
        self.peopleUrl = "XBMC.Container.Update(plugin://plugin.video.xbmb3c?mode=" + str(_MODE_CAST_LIST) + "&id=" + id + ")"
        #self.peopleUrl = "XBMC.RunPlugin(plugin://plugin.video.xbmb3c?mode=" + str(_MODE_CAST_LIST) + "&id=" + id + ")"
        
        try:
            trailerButton = self.getControl(3102)
            if(trailerButton != None):
                if item.get("LocalTrailerCount") != None and item.get("LocalTrailerCount") > 0:
                    itemTrailerUrl = "http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "/LocalTrailers?format=json"
                    jsonData = downloadUtils.downloadUrl(itemTrailerUrl, suppress=False, popup=1 ) 
                    trailerItem = json.loads(jsonData)
                    trailerUrl = server + ',;' + trailerItem[0].get("Id")
                    trailerUrl = urllib.quote(trailerUrl) 
                    self.trailerUrl = "plugin://plugin.video.xbmb3c/?mode=" + str(_MODE_BASICPLAY) + "&url=" + trailerUrl
                else:
                    trailerButton.setEnabled(False)
        except:
            pass

        # all the media stream info
        mediaList = self.getControl(3220)
        
        mediaStreams = item.get("MediaStreams")
        if(mediaStreams != None):
            for mediaStream in mediaStreams:
                if(mediaStream.get("Type") == "Video"):
                    videocodec = mediaStream.get("Codec")
                    if(videocodec == "mpeg2video"):
                        videocodec = "mpeg2"
                    height = str(mediaStream.get("Height"))
                    width = str(mediaStream.get("Width"))
                    aspectratio = mediaStream.get("AspectRatio")
                    fr = mediaStream.get("RealFrameRate")
                    videoInfo = width + "x" + height + " " + videocodec + " " + str(round(fr, 2))
                    listItem = xbmcgui.ListItem("Video:", videoInfo)
                    mediaList.addItem(listItem)
                if(mediaStream.get("Type") == "Audio"):
                    audiocodec = mediaStream.get("Codec")
                    channels = mediaStream.get("Channels")
                    lang = mediaStream.get("Language")
                    audioInfo = audiocodec + " " + str(channels)
                    if(lang != None and len(lang) > 0 and lang != "und"):
                        audioInfo = audioInfo + " " + lang
                    listItem = xbmcgui.ListItem("Audio:", audioInfo)
                    mediaList.addItem(listItem)
                if(mediaStream.get("Type") == "Subtitle"):
                    lang = mediaStream.get("Language")
                    codec = mediaStream.get("Codec")
                    subInfo = codec
                    if(lang != None and len(lang) > 0 and lang != "und"):
                        subInfo = subInfo + " " + lang
                    listItem = xbmcgui.ListItem("Sub:", subInfo)
                    mediaList.addItem(listItem)

        
        #for x in range(0, 10):
        #    listItem = xbmcgui.ListItem("Test:", "Test 02 " + str(x))
        #    mediaList.addItem(listItem)
        
        # add overview
        overview = item.get("Overview")
        self.getControl(3223).setText(overview)
        
        # add people
        peopleList = self.getControl(3230)
        people = item.get("People")

        for person in people:
            displayName = person.get("Name")
            role = person.get("Role")
            id = person.get("Id")
            tag = person.get("PrimaryImageTag")
            
            baseName = person.get("Name")
            baseName = baseName.replace(" ", "+")
            baseName = baseName.replace("&", "_")
            baseName = baseName.replace("?", "_")
            baseName = baseName.replace("=", "_")
            
            actionUrl = "plugin://plugin.video.xbmb3c?mode=" + str(_MODE_PERSON_DETAILS) +"&name=" + baseName
            
            if(tag != None and len(tag) > 0):
                thumbPath = downloadUtils.imageUrl(id, "Primary", 0, 400, 400)
                listItem = xbmcgui.ListItem(label=displayName, label2=role, iconImage=thumbPath, thumbnailImage=thumbPath)
            else:
                listItem = xbmcgui.ListItem(label=displayName, label2=role)
                
            listItem.setProperty("ActionUrl", actionUrl)
            peopleList.addItem(listItem)
        
        # add general info
        infoList = self.getControl(3226)
        listItem = xbmcgui.ListItem("Year:", str(item.get("ProductionYear")))
        infoList.addItem(listItem)
        listItem = xbmcgui.ListItem("Rating:", str(item.get("CommunityRating")))
        infoList.addItem(listItem)        
        listItem = xbmcgui.ListItem("MPAA:", str(item.get("OfficialRating")))
        infoList.addItem(listItem)   
        duration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
        listItem = xbmcgui.ListItem("RunTime:", str(duration) + " Minutes")
        infoList.addItem(listItem) 
        
        genre = ""
        genres = item.get("Genres")
        if(genres != None):
            for genre_string in genres:
                if genre == "": #Just take the first genre
                    genre = genre_string
                else:
                    genre = genre + " / " + genre_string

        listItem = xbmcgui.ListItem("Genre:", genre)
        infoList.addItem(listItem) 
        
        path = item.get('Path')
        listItem = xbmcgui.ListItem("Path:", path)
        infoList.addItem(listItem)
        
        # add resume percentage text to name
        addResumePercent = __settings__.getSetting('addResumePercent') == 'true'
        if (addResumePercent and cappedPercentage != None):
            name = name + " (" + str(cappedPercentage) + "%)"        

        self.getControl(3000).setLabel(name)
        self.getControl(3003).setLabel(episodeInfo)
        self.getControl(3001).setImage(fanArt)
        
        if(type == "Episode"):
            self.getControl(3009).setImage(image)
            if(cappedPercentage != None):
                self.getControl(3010).setImage("Progress\progress_" + str(cappedPercentage) + ".png")
        else:
            self.getControl(3011).setImage(image)
            if(cappedPercentage != None):
                self.getControl(3012).setImage("Progress\progress_" + str(cappedPercentage) + ".png")
                
        # disable play button
        if(type == "Season" or type == "Series"):
            self.setFocusId(3226)
            self.getControl(3002).setEnabled(False)                
        
    def setId(self, id):
        self.id = id
        
    def onFocus(self, controlId):      
        pass
        
    def doAction(self):
        pass

    def closeDialog(self):
        self.close()
        
    def onClick(self, controlID):
        
        if(controlID == 3002):
           
            # close all dialogs when playing an item
            xbmc.executebuiltin("Dialog.Close(all,true)")
            
            xbmc.executebuiltin("RunPlugin(" + self.playUrl + ")")
            self.close()
            
        elif(controlID == 3102):
           
            # close all dialogs when playing an item
            xbmc.executebuiltin("Dialog.Close(all,true)")
            
            xbmc.executebuiltin("RunPlugin(" + self.trailerUrl + ")")
            self.close()
        elif(controlID == 3230):
        
            peopleList = self.getControl(3230)
            item = peopleList.getSelectedItem()
            action = item.getProperty("ActionUrl")
            
            xbmc.log(action)
            xbmc.executebuiltin("RunPlugin(" + action + ")")
        
        pass
        
