import gtk
import gobject

from urlparse import urlparse
import mimetypes
import filesMetadata
from notifications import *

class DeviceEngine:

    def __init__(self, _device):
        self.__device = _device
        self.__track_listing_model = None
        self.__file_tree_model = None

    def connect_device(self):
        if not self.__device.connect():
            return False
        self.update_models()
        return True

    def disconnect_device(self):
        self.__track_listing_model = None
        self.__file_tree_model = None
        self.__device.close()

    def update_models(self):
        tracks_list =  self.__device.get_tracklisting()
        self.__create_track_listing_model(tracks_list)
        #self.__create_file_tree_model(file_list)

    def __create_track_listing_model(self, tracks_list):
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        for track in tracks_list:
            model.append(track)
        self.__track_listing_model = model

    def __create_file_tree_model(self, file_list):
        #@TODO
        pass

    def get_track_listing_model(self):
        return self.__track_listing_model

    def get_file_tree_model(self):
        return self.__file_tree_model

    def send_file(self, file_url, callback):
        url = urlparse(file_url)
        """ TODO check mimetype to get metadata:
        mimetypes.init()
        mimetypes.guess_type(filename) =  'audio/mpeg'"""
        #TODO: find correct metadata
        metadata = filesMetadata.get_metadata_for_type(url.path)
        self.__device.send_track(metadata, callback)

    def del_file(self, file_id):
        self.__device.remove_track(file_id)

    def get_device(self):
        return self.__device

