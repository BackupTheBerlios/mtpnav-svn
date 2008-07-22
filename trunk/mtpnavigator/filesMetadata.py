import os.path

def get_metadata_for_type(path):
        path = os.path.normpath(path)
        filename = os.path.split(path)[1]
        extension = os.path.splitext(filename)[1]
        if extension == ".mp3": #FIXME: use mimetype? MP3, others?
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
        self.date = None #@TODO
        self.title =  self.filename
        self.artist = None
        self.directoryID = 0 #@TODO
        self.album = None
        self.genre = None
        self.tracknumber = None
        self.duration = None
        self.samplerate = None
        self.nochannels = None
        self.bitrate = None
        self.bitratetype = None
        self.rating = None
        self.usecount = None

class MP3FileMetadata(GenericFileMetadata):

    def __init__(self, path, filename, extension):
        GenericFileMetadata. __init__(self, path, filename, extension)

        #@TODO: get mp3 metadata
        self.title =  os.path.splitext(self.filename)[0]
        self.date = None
        self.artist = "baba"
        self.album = "toto"
        self.genre = "tata"

class OggFileMetadata(GenericFileMetadata):

    def __init__(self, path, filename, extension):
        GenericFileMetadata. __init__(self, path, filename, extension)

        #@TODO: get ogg metadata
        self.title =  self.filename
        self.date = None
        self.album = "ogg"
        self.genre = "oggi"





