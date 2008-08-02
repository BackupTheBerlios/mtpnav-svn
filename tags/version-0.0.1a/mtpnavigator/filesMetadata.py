import os.path
from notifications import *

# for mp3 files
has_eyed3 = True
try:
    import eyeD3
except:
    notify_warning("Install python-eyeD3 if you want to get mp3 tags")
    has_eyed3 = False

def get_metadata_for_type(path):
        path = os.path.normpath(path)
        filename = os.path.split(path)[1]
        extension = os.path.splitext(filename)[1]
        #FIXME: use mimetype? MP3, others?
        #mimetypes.init()
        #mimetypes.guess_type(filename) =  'audio/mpeg'"""
        if extension == ".mp3" and has_eyed3:
            return MP3FileMetadata(path, filename, extension)
        elif extension == ".ogg":
            return OggFileMetadata(path, filename, extension)
        else:
            return GenericFileMetadata(path, filename, extension)


class GenericFileMetadata:

    def __init__(self, path, filename, extension):
        self.path = path
        self.filename = filename
        self.extension = extension
        self.directoryID = 0 #@TODO

        # get metadata from path and file name
        # todo: parametrize how it should be done for nom consider .../artiste/album/title.mp3
        self.title =  self.filename
        (path, tail) = os.path.split(path)
        self.album = tail
        (path, tail) = os.path.split(path)
        self.artist = tail
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

class MP3FileMetadata(GenericFileMetadata):

    def __init__(self, path, filename, extension):
        GenericFileMetadata. __init__(self, path, filename, extension)

        tag = eyeD3.tag.Tag()
        try:
            if tag.link(path): # tags are present
                if DEBUG:
                    debug_trace("Mp3 tags found for file %s" % filename, sender=self)
                self.title =  tag.getTitle()
                self.album = tag.getAlbum()
                self.artist = tag.getArtist()
                if tag.getGenre(): self.genre = tag.getGenre().getName()
                self.date = tag.getDate()
                self.tracknumer = 0 #TODO: convert int tag.getTrackNum()
                self.duration = 0 # todo
                mp3 = eyeD3.tag.Mp3AudioFile(path)
                self.samplerate = mp3.getSampleFreq()
                (variable, bitrate) = mp3.getBitRate()
                self.bitrate = bitrate
                self.bitratetype = 1
                if variable:
                    self.bitratetype = 2
                if tag.getPlayCount(): self.usecount = tag.getPlayCount()
                self.year = tag.getYear()
            elif DEBUG:
                debug_trace("No tag found for mp3 file %s" % filename, sender=self)
        except Exception, exc:
            notify_error("Error while getting mp3 tags for file %s" % filename, exc)
        finally:
            if DEBUG:
                debug_trace("Tags are %s" % self.to_string(), sender=self)

class OggFileMetadata(GenericFileMetadata):

    def __init__(self, path, filename, extension):
        GenericFileMetadata. __init__(self, path, filename, extension)

        #@TODO: get ogg metadata
        self.title =  self.filename
        self.date = None
        self.album = "ogg"
        self.genre = "oggi"





