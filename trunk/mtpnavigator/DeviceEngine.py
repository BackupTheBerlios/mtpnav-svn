import gtk
import gobject

from urlparse import urlparse
import mimetypes
import filesMetadata
from notifications import *

class DeviceEngine:

    def __init__(self, _device):
        self.__device = _device
        self.__track_listing_model = TrackListingModel(_device)
        self.__file_tree_model = None

    def connect_device(self):
        if not self.__device.connect():
            return False
        if DEBUG: debug_trace("Device connected successfully", sender=self)
        self.update_models()
        return True

    def disconnect_device(self):
        self.__track_listing_model = None
        self.__file_tree_model = None
        self.__device.close()

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

class TrackListingModel(ListStore):
    self.OBJECT_ID=0
    self.TITLE=1
    self.ARTIST=2
    self.LENGTH=3
    self.DATE=4
    
    def __init__(self, _device):
        ListStore.__init__(gobject.TYPE_UINT, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        tracks_list =  self.__device.get_tracklisting()
        self.__cache = {}
        for track in tracks_list:
            iter = self.append(track)
            self.__cache[track[0]] = TreeRowReference(self, self.get_path(iter)
            
    def __get_iter(self, object_id):
        try:
            return  self.__cache[object_id]
        except KeyError, exc:
            return None
        #FIXME: use pair {id, TreeRowReference} to cache rows?
        #it = self.get_iter_first()
        #while it
        #    if self.get_value(it, self.OBJECT_ID) == object_id:
        #        return it
        #    it = self.iter_next()
        #return None
        
    def remove_object(self, object_id):
        it = __get_iter(object_id)
        if it:
            self.remove(it)
        else:
            notify_warning("trying to remove non existing object %s from model", object_id)
            
    def add_row(self, object_id, title, artist, length, date):
        self.append([object_id, title, artist, length, date])
        

        
        
        