import gtk
import gobject

from urlparse import urlparse
import mimetypes



class DeviceEngine:

    def __init__(self, _device):
        self.__device = _device
        self.__track_listing_model = None

    def connect_device(self):
        if not self.__device.connect():
            return False
        self.__fetch_data()
        return True

    def disconnect_device(self):
        self.__track_listing_model = None
        self.__device.close()

    def __fetch_data(self):
        tracks_list =  self.__device.get_tracklisting()
        self.__create_track_listing_model(tracks_list)

    def __create_track_listing_model(self, tracks_list):
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        for track in tracks_list:
            model.append(track)
        self.__track_listing_model = model

    def get_track_listing_model(self):
        return self.__track_listing_model

    def get_file_tree_model(self):
        pass

    def send_file(self, file_url):
        print "adding %s", file_url
        url = urlparse(file_url)
        if url.scheme != "file://":
            print "not a local file"
            return
        """ TODO check mimetype to get metadata: 
        mimetypes.init()
        mimetypes.guess_type(filename) =  'audio/mpeg'"""
        metadata=None
        self.__device.add_track(url.path, metadata)
        self.__track_listing_model.append([file_url,"","",""])

    def get_device(self):
        return self.__device
