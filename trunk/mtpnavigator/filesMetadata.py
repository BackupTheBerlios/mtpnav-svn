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
        (path, tail) = split(path)
        self.album = tail
        (path, tail) = split(path)
        self.artist = tail
        self.genre = None
        self.date = None
        self.tracknumber = None
        self.duration = None
        self.samplerate = None
        self.bitrate = None
        self.bitratetype = None # 0 = unused, 1 = constant, 2 = VBR, 3 = free
        self.rating = None
        self.usecount = None
        self.year = None

class MP3FileMetadata(GenericFileMetadata):

    def __init__(self, path, filename, extension):
        GenericFileMetadata. __init__(self, path, filename, extension)

        tag = eyeD3.tag.Tag()
        try:
            if tag.link(filename): # tags are present
                self.title =  tag.getTitle()
                self.album = tag.getAlbum
                self.artist = tag.getArtist()
                self.genre = tag.getGenre().getName()
                self.date = tag.getDate()
                self.tracknumer = tag.getTrackNum()
                self.duration = None # todo
                self.samplerate = tag.getSampleFreq()
                (variable, bitrate) = tag.getBitRate()
                self.bitrate = bitrate
                self.bitratetype = 1
                if variable:
                    self.bitratetype = 2
                self.usecount = tag.getPlayCount()
                self.year = tag.getYear()
            else:
                debug_trace("No tag found for mp3 file %s" % filename, sender=self)
        except Exception, exc:
            notify_warning("Error while getting mp3 tags for file %s" % filename, exc)

class OggFileMetadata(GenericFileMetadata):

    def __init__(self, path, filename, extension):
        GenericFileMetadata. __init__(self, path, filename, extension)

        #@TODO: get ogg metadata
        self.title =  self.filename
        self.date = None
        self.album = "ogg"
        self.genre = "oggi"





