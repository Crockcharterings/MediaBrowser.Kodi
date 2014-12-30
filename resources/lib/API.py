# API.py
# This class helps translate more complex cases from the MediaBrowser API to the XBMC API

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import os
import json
import threading
import sys
from datetime import datetime
import urllib
from DownloadUtils import DownloadUtils
from Database import Database
from urlparse import urlparse


logLevel = 1
__settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
__addon__       = xbmcaddon.Addon(id='plugin.video.xbmb3c')

CP_ADD_URL = 'XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?title=%s)'

__cwd__ = __settings__.getAddonInfo('path')
PLUGINPATH = xbmc.translatePath( os.path.join( __cwd__) )
__language__     = __addon__.getLocalizedString

class API():
    
    def getPeople(self, item):
        # Process People
        director=''
        writer=''
        cast=[]
        people = item.get("People")
        if(people != None):
            for person in people:
                if(person.get("Type") == "Director"):
                    director = director + person.get("Name") + ' ' 
                if(person.get("Type") == "Writing"):
                    writer = person.get("Name")
                if(person.get("Type") == "Writer"):
                    writer = person.get("Name")                 
                    if(person.get("Type") == "Actor"):
                        Name = person.get("Name")
                        Role = person.get("Role")
                        if Role == None:
                            Role = ''
                        cast.append(Name)
        return  {'Director'  : director, 
                'Writer'    : writer,
                'Cast'      : cast
                }

    def getTimeInfo(self, item):
        resumeTime = ''
        userData = item.get("UserData")
        PlaybackPositionTicks = '100'
        if userData.get("PlaybackPositionTicks") != None:
            PlaybackPositionTicks = str(userData.get("PlaybackPositionTicks"))
            reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
            resumeTime = reasonableTicks / 10000    

        try:
            tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
        except TypeError:
            try:
                tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
            except TypeError:
                tempDuration = "0"
        cappedPercentage = None
        resume=0
        percentage=0
        if (resumeTime != "" and int(resumeTime) > 0):
            duration = float(tempDuration)
            if(duration > 0):
                resume = float(resumeTime) / 60
                percentage = int((resume / duration) * 100.0)
        return {'Duration'      : tempDuration, 
                'TotalTime'     : tempDuration,
                'Percent'       : str(percentage),
                'ResumeTime'    : str(resume)
               }

    def getStudio(self, item):
        # Process Studio
        studio = "" 
        if item.get("SeriesStudio") != None and item.get("SeriesStudio") != '':
            studio = item.get("SeriesStudio")
        if studio == "":        
            studios = item.get("Studios")
            if(studios != None):
                for studio_string in studios:
                    if studio=="": #Just take the first one
                        temp=studio_string.get("Name")
                        studio=temp.encode('utf-8')
        return studio

    def getMediaStreams(self, item, mediaSources=False):    
        # Process MediaStreams
        channels = ''
        videocodec = ''
        audiocodec = ''
        height = ''
        width = ''
        aspectratio = '1:1'
        aspectfloat = 1.85

        if mediaSources == True:
            mediaSources = item.get("MediaSources")
            if(mediaSources != None):
                MediaStreams = mediaSources[0].get("MediaStreams")
            else:
                MediaStreams = None
        else:
            MediaStreams = item.get("MediaStreams")
        if(MediaStreams != None):
            #mediaStreams = MediaStreams[0].get("MediaStreams")
            if(MediaStreams != None):
                for mediaStream in MediaStreams:
                    if(mediaStream.get("Type") == "Video"):
                        videocodec = mediaStream.get("Codec")
                        height = str(mediaStream.get("Height"))
                        width = str(mediaStream.get("Width"))
                        aspectratio = mediaStream.get("AspectRatio")
                        if aspectratio != None and len(aspectratio) >= 3:
                            try:
                                aspectwidth,aspectheight = aspectratio.split(':')
                                aspectfloat = float(aspectwidth) / float(aspectheight)
                            except:
                                aspectfloat = 1.85
                    if(mediaStream.get("Type") == "Audio"):
                        audiocodec = mediaStream.get("Codec")
                        channels = mediaStream.get("Channels")
        return {'channels'      : str(channels), 
                'videocodec'    : videocodec, 
                'audiocodec'    : audiocodec, 
                'height'        : height,
                'width'         : width,
                'aspectratio'   : str(aspectfloat)
                }
                
    def getUserData(self, item):
        userData = item.get("UserData")
        resumeTime = 0
        if(userData != None):
            if userData.get("Played") != True:
                watched="True"
            else:
                watched="False"
            if userData.get("IsFavorite") == True:
                favorite="True"
            else:
                favorite="False"
            if(userData.get("Played") == True):
                playcount="1"
            else:
                playcount="0"
            if userData.get('UnplayedItemCount') != None:
                UnplayedItemCount = userData.get('UnplayedItemCount')
            else:
                UnplayedItemCount = 0
            if userData.get('PlaybackPositionTicks') != None:
                PlaybackPositionTicks = userData.get('PlaybackPositionTicks')
            else:
                PlaybackPositionTicks = ''
        return  {'Watched'  :   watched,
                 'Favorite' :   favorite,
                 'PlayCount':   playcount,
                 'UnplayedItemCount' : UnplayedItemCount,
                 'PlaybackPositionTicks' : str(PlaybackPositionTicks)
                }
    
    def getGenre(self,item):
        genre = ""
        genres = item.get("Genres")
        if(genres != None and genres != []):
            for genre_string in genres:
                if genre == "": 
                    genre = genre_string
                elif genre_string != None:
                    genre = genre + " / " + genre_string   
        return genre
        
    def getName(self, item):
        Temp = item.get("Name")
        if Temp == None:
            Temp = ""
        Name=Temp.encode('utf-8')
        return Name
    
    def getSeriesName(self, item):
        Temp = item.get("SeriesName")
        if Temp == None:
            Temp = ""
        Name=Temp.encode('utf-8')
        return Name        
        
    def getOverview(self, item):
        Temp = item.get("Overview")
        if Temp == None:
            Temp=''
        Overview1=Temp.encode('utf-8')
        Overview=str(Overview1)
        return Overview
        
    def getPremiereDate(self, item):
        if(item.get("PremiereDate") != None):
            premieredatelist = (item.get("PremiereDate")).split("T")
            premieredate = premieredatelist[0]
        else:
            premieredate = ""
        return premieredate.decode("utf-8")
        
    def getTVInfo(self, item, userData):
        TotalSeasons     = 0 if item.get("ChildCount")==None else item.get("ChildCount")
        TotalEpisodes    = 0 if item.get("RecursiveItemCount")==None else item.get("RecursiveItemCount")
        WatchedEpisodes  = 0 if userData.get("UnplayedItemCount")==None else TotalEpisodes-userData.get("UnplayedItemCount")
        UnWatchedEpisodes = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")
        NumEpisodes      = TotalEpisodes
        tempEpisode = ""
        if (item.get("IndexNumber") != None):
            episodeNum = item.get("IndexNumber")
            if episodeNum < 10:
                tempEpisode = "0" + str(episodeNum)
            else:
                tempEpisode = str(episodeNum)
                
        tempSeason = ""
        if (str(item.get("ParentIndexNumber")) != None):
            tempSeason = str(item.get("ParentIndexNumber"))
            if item.get("ParentIndexNumber") < 10:
                tempSeason = "0" + tempSeason
        if item.get("SeriesName") != None:
            temp=item.get("SeriesName")
            SeriesName=temp.encode('utf-8')
        else:
            SeriesName=''
        return  {'TotalSeasons'     :   str(TotalSeasons),
                 'TotalEpisodes'    :   str(TotalEpisodes),
                 'WatchedEpisodes'  :   str(WatchedEpisodes),
                 'UnWatchedEpisodes':   str(UnWatchedEpisodes),
                 'NumEpisodes'      :   str(NumEpisodes),
                 'Season'           :   tempSeason,
                 'Episode'          :   tempEpisode,
                 'SeriesName'       :   SeriesName
                 }
    def getDate(self, item):
        tempDate = item.get("DateCreated")
        if tempDate != None:
            tempDate = tempDate.split("T")[0]
            date = tempDate.split("-")
            tempDate = date[2] + "." + date[1] + "." +date[0]
        else:
            tempDate = "01.01.2000"
        return tempDate