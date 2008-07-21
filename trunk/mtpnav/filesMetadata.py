class FileMetadata:
    
    def __init__(self, path):    
        self.path = path
        (self.filename, self.extension) = self.__parse_filename(path)
        self.date = None #@TODO
        self.title =  self.filename
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

    def __get_file_name_from_path(path):
        #@TODO
        return ("Test", "mp3")
        
class MP3FileMetadata
    def __init__(self, path):    
        #@TODO: get mp3 metadata
        self.title =  self.filename
        self.date = None
        self.album = None
        self.genre = None
        
class OggFileMetadata
    def __init__(self, path):    
        #@TODO: get mp3 metadata
        self.title =  self.filename
        self.date = None
        self.album = None
        self.genre = None        
        
      
        
        
         
