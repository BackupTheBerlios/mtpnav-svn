import os.path
from notifications import *

# for mp3 files
has_eyed3 = True
try:
    import eyeD3
except:
    notify_warning("Install python-eyeD3 if you want to get mp3 tags")
    has_eyed3 = False

has_pymtp = True
try:
    import pymtp
    import mtpDevice
except:
    has_pymtp = False

TYPE_UNKNOW=0
TYPE_FOLDER=1
TYPE_PLAYLIST=2
TYPE_FOLDER=3
TYPE_FILE=4
TYPE_TRACK=5


class Metadata:
    def __init__(self):
        self.id = None
        self.parent_id = None
        self.path = None # path + filename + extension
        self.filename = None # filename + extension
        self.extension = None
        self.type = TYPE_UNKNOW
        self.title =  None
        self.album = None
        self.artist = None
        self.genre = None
        self.date = None
        self.filesize = 0
        self.tracknumber = 0
        self.duration = 0
        self.samplerate = 0
        self.bitrate = 0
        self.bitratetype = 0 # 0 = unused, 1 = constant, 2 = VBR, 3 = free
        self.rating = 0
        self.usecount = 0
        self.year = None

    def to_MTPTrack(self):
        mtp_metadata = pymtp.LIBMTP_Track()
        mtp_metadata.parent_id=0
        if self.parent_id:
            mtp_metadata.parent_id = int(self.parent_id)
        mtp_metadata.title = self.title
        mtp_metadata.artist = self.artist
        mtp_metadata.album = self.album
        mtp_metadata.genre = self.genre
        mtp_metadata.date = mtpDevice.date_to_mtp(self.date)
        mtp_metadata.filesize = self.filesize
        mtp_metadata.tracknumber =self.tracknumber
        mtp_metadata.duration = self.duration
        mtp_metadata.samplerate = self.samplerate
        mtp_metadata.bitrate = self.bitrate
        mtp_metadata.bitratetype = self.bitratetype
        mtp_metadata.rating = self.rating
        mtp_metadata.usecount = self.usecount
        return mtp_metadata

    if DEBUG:
        def to_string(self):
            str = ""
            str += " id=" + self.id
            if self.parent_id: str += " parent_id=" + self.parent_id
            if self.title: str += " title=" + self.title
            if self.album: str += " album=" + self.album
            if self.artist: str += " artist="+ self.artist
            if self.genre: str += " genre=" + self.genre
            return str

def get_from_MTPTrack(track):
    m = Metadata()
    m.id = str(track.item_id)
    m.type = TYPE_TRACK    
    m.title = track.title
    if not m.title or m.title=="": m.title=track.filename
    m.artist = track.artist
    m.album = track.album
    m.genre = track.genre
    m.filesize = track.filesize
    m.date = "" #FIXME: self.__mtp_to_date(track.date)
    if DEBUG: debug_trace("Metadata gotten from MTPtrack. They are %s" % m.to_string())
    return m

def get_from_MTPFolder(folder):
    m = Metadata()
    m.id = str(folder.folder_id)
    m.parent_id = str(folder.parent_id)
    m.type = TYPE_FOLDER 
    m.title = folder.name
    if DEBUG: debug_trace("Metadata gotten from MTPfolder. They are %s" % m.to_string())
    return m

def get_from_MTPFile(file):
    m = Metadata()
    m.type = TYPE_FILE
    m.id = str(file.item_id)
    m.parent_id = str(file.parent_id)
    m.title = file.filename
    m.filesize = file.filesize
    if DEBUG: debug_trace("Metadata gotten from MTPfile. They are %s" % m.to_string())
    return m

def get_from_file(path):
    m = Metadata()
    m.path = os.path.normpath(path)
    m.id = m.path
    m.filename = os.path.split(path)[1]
    m.extension = os.path.splitext(m.filename)[1]
    #FIXME: use mimetype? extension, others?
    #mimetypes.init()
    #mimetypes.guess_type(filename) =  'audio/mpeg'"""
    is_audio_file = (m.extension in (".mp3", ".ogg", ".wav"))
    if is_audio_file:
        m.type = TYPE_TRACK
    else:
        m.type = TYPE_FILE
    
    if m.extension == ".mp3" and has_eyed3:
        return __get_from_MP3tags(m)
    elif m.extension == ".ogg":
        return __get_from_oggtags(m)
    else:
        return __get_from_filepath(m)

def __get_from_filepath(m):
        # todo: parametrize how it should be done for nom consider .../artiste/album/title.mp3
        m.title =  m.filename
        (path, tail) = os.path.split(os.path.split(m.path)[0])
        m.album = tail
        (path, tail) = os.path.split(path)
        m.artist = tail
        if DEBUG: debug_trace("Tags gotten from file. They are %s" % m.to_string())
        return m

def __get_from_MP3tags(m):
        tag = eyeD3.tag.Tag()
        try:
            if tag.link(m.path): # tags are present
                if DEBUG:
                    debug_trace("Mp3 tags found for file %s" % m.filename)
                m.title =  tag.getTitle()
                m.album = tag.getAlbum()
                m.artist = tag.getArtist()
                if tag.getGenre(): m.genre = tag.getGenre().getName()
                m.date = tag.getDate()
                m.tracknumer = 0 #TODO: convert int tag.getTrackNum()
                m.filesize = 0 # todo
                m.duration = 0 # todo
                mp3 = eyeD3.tag.Mp3AudioFile(m.path)
                msamplerate = mp3.getSampleFreq()
                (variable, m.bitrate) = mp3.getBitRate()
                m.bitratetype = 1
                if variable:
                    m.bitratetype = 2
                if tag.getPlayCount(): m.usecount = tag.getPlayCount()
                m.year = tag.getYear()
                if DEBUG: debug_trace("Tags gotten from mp3. They are %s" % m.to_string())
                return m
            elif DEBUG:
                debug_trace("No tag found for mp3 file %s" % m.filename)
                return __get_from_filepath(m)
        except Exception, exc:
            notify_error("Error while getting mp3 tags for file %s" % m.filename, exc)
            return __get_from_filepath(m)

def __get_from_oggtags(m):
        m = Metadata()
        #TODO
        return __get_from_filepath(m)





