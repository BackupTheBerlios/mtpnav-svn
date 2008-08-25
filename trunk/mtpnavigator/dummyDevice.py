from notifications import *
from Metadata import *
import DeviceEngine

ERRMSG_UNKNOW = "The device returned an unknow error" #TRANSLATE
ERRMSG_DEVICE_FULL = "Not enought free space on device" #TRANSLATE
ERRMSG_ALREADY_EXIST = "Already exists on the device" #TRANSLATE


class DummyDevice():
    folder_listing = [(1, 0, "Music"), (2, 0 , "System")]
    file_listing = [(True, 10, 1, "TEST.MP3", "title", "artist", "album", "genre", 1231, 123454),
                     (True, 11, 2, "system.sys", "", "", "", "", 0, 0)]
    file_next_id = 12
    DEFAULT_MUSIC_FOLDER = 1

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
        for track in self.file_listing:
            m = Metadata()
            if track[0]:
                m.id = str(track[1])
                m.type = TYPE_TRACK
                m.parent_id = str(track[2])
                m.filename = track[3]
                m.title = track[4]
                m.artist = track[5]
                m.album = track[6]
                m.genre = track[7]
                m.filesize = track[8]
                m.date = track[9]
                tracks.append(m)
        return tracks

    def get_folder_listing(self):
        folders=[]
        for folder in self.folder_listing:
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
        return playlists

    def get_tracks_for_playlist(self, playlist):
        pass
        
    def get_file_listing(self):
        files = []
        for file in self.file_listing:
            m = Metadata()
            m.id = str(file[1])
            m.type = TYPE_FILE
            m.parent_id = str(file[2])
            m.filename = file[3]
            m.title = file[3]
            files.append(m)
        return files
        
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