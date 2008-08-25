from notifications import *
from Metadata import *
import DeviceEngine

ERRMSG_UNKNOW = "The device returned an unknow error" #TRANSLATE
ERRMSG_DEVICE_FULL = "Not enought free space on device" #TRANSLATE
ERRMSG_ALREADY_EXIST = "Already exists on the device" #TRANSLATE


class DummyDevice():
    FOLDER_LISTING = [(1, 0, "Music"), (2, 0 , "System"), (3, 1, "Test folder")]
    DEFAULT_MUSIC_FOLDER = 1

    FILE_LISTING = {10: (True, 1, "TEST.MP3", "title", "artist", "album", "genre", 1231, 123454),
                    11: (True, 2, "system.sys", "", "", "", "", 0, 0),
                    12: (True, 1, "TEST2.MP3", "title2", "artist2", "album2", "genre2", 2222, 123454),
                    13: (True, 3, "TEST3.MP3", "title3", "artist3", "album3", "genre3", 3333, 123454),
                    14: (True, 3, "TEST4.MP3", "title4", "artist4", "album4", "genre4", 4444, 123454)
                    }

    PLAYLIST_LISTING = {12: (0, "testPL", [10,12,13])}

    object_next_id = 13

    def __init__(self):
        pass

    def get_name(self):
        return "Test device"

    def connect(self):
        debug_trace("Dummy connected")

    def disconnect(self):
        debug_trace("Dummy disconnected")

    def send_track(self, metadata=None, callback=None):
        TOTAL = 10000
        for i in range(0,TOTAL):
            callback(i, TOTAL)
        file_next_id+=1
        file_listing.append((True, file_next_id, DEFAULT_MUSIC_FOLDER, m.filename, m.title, m.artist, m.album, m.genre, m.filesize, m.date))
        m.id=str(file_next_id)
        m.parent_id = str(DEFAULT_MUSIC_FOLDER)
        return m            
        
    def create_folder(self, metadata=None):
        pass
    
    def create_playlist(self, metadata):
        pass

    def add_track_to_playlist(self, metadata):
        pass

    def remove_object(self, object_id):
        pass

    def get_track_listing(self):
        tracks = []
        for track_id in self.FILE_LISTING.keys():
            track=self.FILE_LISTING[track_id]
            m = Metadata()
            if track[0]:
                m.id = str(track_id)
                m.type = TYPE_TRACK
                m.parent_id = str(track[1])
                m.filename = track[2]
                m.title = track[3]
                m.artist = track[4]
                m.album = track[5]
                m.genre = track[6]
                m.filesize = track[7]
                m.date = track[8]
                tracks.append(m)
        return tracks

    def get_folder_listing(self):
        folders=[]
        for folder in self.FOLDER_LISTING:
            m = Metadata()
            m.id = str(folder[0])
            m.parent_id = str(folder[1])
            m.type = TYPE_FOLDER
            m.filename = folder[2]
            m.title = folder[2]
            folders.append(m)
        return folders

    def get_playlist_listing(self):
        playlists=[]
        for id in self.PLAYLIST_LISTING.keys():
            playlist=self.PLAYLIST_LISTING[id]
            m = Metadata()
            m.id = str(id)
            m.parent_id = str(playlist[0])
            m.type = TYPE_PLAYLIST
            m.filename = str(playlist[1])
            m.title = str(playlist[1])
            playlists.append(m)
        return playlists

    def get_tracks_for_playlist(self, playlist_meta):
        playlist=self.PLAYLIST_LISTING[int(playlist_meta.id)]
        tracks=[]
        for track_id in playlist[2]:
            tracks.append(self.__get_file_metadata(track_id))
        return tracks
        
    def get_file_listing(self):
        files = []
        for file_id in self.FILE_LISTING.keys():
            m = self.__get_file_metadata(file_id)
            files.append(m)
        return files
        
    def __get_file_metadata(self, file_id):
        file=self.FILE_LISTING[file_id]
        m = Metadata()
        m.id = str(file_id)
        m.type = TYPE_FILE
        m.parent_id = str(file[1])
        m.filename = file[2]
        m.title = file[2]
        return m
        
    def get_diskusage(self):
        return [752,1000]

    def get_usedspace(self):
        return 752

    def get_batterylevel(self):
        return [100,23]

    def get_information(self):
        info = []
        info.append(["Owner name", "Jerome Chabod"]) #TRANSLATE
        info.append(["Manufacturer", "MTPnavigator"]) #TRANSLATE
        info.append(["Model name", "Dummy"]) #TRANSLATE
        info.append(["Serial number", "123456"]) #TRANSLATE
        info.append(["Firmware version", "0.01"]) #TRANSLATE
        return info

    def __check_free_space(self, objectsize):
        return objectsize <= self.__MTPDevice.get_freespace()

    def __file_exist(self, filename):
        file_names = []
        for file in self.get_file_listing():
             file_names.append(file.title)
        return filename in file_names