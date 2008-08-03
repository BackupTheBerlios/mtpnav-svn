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
except:
    has_pymtp = False

class Metadata:
    def __init__(self):
        self.path = None # path + filename + extension
        self.filename = None # filename + extension
        self.extension = None
        self.title =  None
        self.album = None
        self.artist = None
        self.genre = None
        self.date = None
        self.tracknumber = 0
        self.duration = 0
        self.samplerate = 0
        self.bitrate = 0
        self.bitratetype = 0 # 0 = unused, 1 = constant, 2 = VBR, 3 = free
        self.rating = 0
        self.usecount = 0
        self.year = None

    if DEBUG:
        def to_string(self):
            str = ""
            if self.title: str += " title=" + self.title
            if self.album: str += " album=" + self.album
            if self.artist: str += " artist="+ self.artist
            if self.genre: str += " genre=" + self.genre
            return str

def get_from_file(path):
    m = Metadata()
    m.path = os.path.normpath(path)
    m.filename = os.path.split(path)[1]
    m.extension = os.path.splitext(m.filename)[1]
    #FIXME: use mimetype? MP3, others?
    #mimetypes.init()
    #mimetypes.guess_type(filename) =  'audio/mpeg'"""
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
        if DEBUG: debug_trace("Tags gotten from file. They are %s" % m.to_string(), sender="Metadate")
        return m

def __get_from_MP3tags(m):
        tag = eyeD3.tag.Tag()
        try:
            if tag.link(m.path): # tags are present
                if DEBUG:
                    debug_trace("Mp3 tags found for file %s" % m.filename, sender="Metadate")
                m.title =  tag.getTitle()
                m.album = tag.getAlbum()
                m.artist = tag.getArtist()
                if tag.getGenre(): m.genre = tag.getGenre().getName()
                m.date = tag.getDate()
                m.tracknumer = 0 #TODO: convert int tag.getTrackNum()
                m.duration = 0 # todo
                mp3 = eyeD3.tag.Mp3AudioFile(m.path)
                msamplerate = mp3.getSampleFreq()
                (variable, m.bitrate) = mp3.getBitRate()
                m.bitratetype = 1
                if variable:
                    m.bitratetype = 2
                if tag.getPlayCount(): m.usecount = tag.getPlayCount()
                m.year = tag.getYear()
                if DEBUG: debug_trace("Tags gotten from mp3. They are %s" % m.to_string(), sender="Metadate")
                return m
            elif DEBUG:
                debug_trace("No tag found for mp3 file %s" % m.filename, sender="Metadate")
                return __get_from_filepath(m)
        except Exception, exc:
            notify_error("Error while getting mp3 tags for file %s" % m.filename, exc)
            return __get_from_filepath(m)

class OggFileMetadata():

    def __init__(self):
        m = Metadata()
        #TODO
        return __get_from_filepath(m)





