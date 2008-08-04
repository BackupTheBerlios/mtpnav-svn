import gtk
import gobject

from urlparse import urlparse
import mimetypes
import filesMetadata
from notifications import *
import util

class DeviceEngine:

    def __init__(self, _device):
        self.__device = _device
        self.__file_tree_model = None

    def connect_device(self):
        if not self.__device.connect():
            return False
        if DEBUG: debug_trace("Device connected successfully", sender=self)
        self.__track_listing_model = TrackListingModel(self.__device)
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
        metadata = filesMetadata.get_metadata_for_type(url.path)
        return self.__device.send_track(metadata, callback)

    def del_file(self, file_id):
        return self.__device.remove_track(file_id)

    def get_device(self):
        return self.__device

class TrackListingModel(gtk.ListStore):
    OBJECT_ID=0
    TITLE=1
    ARTIST=2
    ALBUM=3
    GENRE=4
    LENGTH_STR=5
    LENGTH_INT=6
    DATE=7

    def __init__(self, _device):
        gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT, gobject.TYPE_STRING)
        self.__cache = {}
        tracks_list =  _device.get_tracklisting()
        for track in tracks_list:
            self.add_row(track[0], track[1], track[2], track[3], track[4], track[5], track[6])

    def append(self, track):
        iter = gtk.ListStore.append(self, track)
        self.__cache[track[0]] = gtk.TreeRowReference(self, self.get_path(iter))
        return iter

    def __get_iter(self, object_id):
        try:
            return  self.get_iter(self.__cache[object_id].get_path())
        except KeyError, exc:
            return None

    def remove_object(self, object_id):
        it = self.__get_iter(object_id)
        if it:
            self.remove(it)
        else:
            debug_trace("trying to remove non existing object %s from model" % object_id, sender=self)

    def add_row(self, object_id, title, artist, album, genre, length, date):
        self.append([object_id, title, artist, album, genre, util.format_filesize(length), length, date])




