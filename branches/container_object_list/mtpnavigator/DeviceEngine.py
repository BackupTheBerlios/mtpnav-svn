import gtk
import gobject

from urlparse import urlparse
import mimetypes
import Metadata
from notifications import *
import util
from threading import Lock
import datetime

class DeviceError(Exception):
    """
        genereal device error
    """
    pass

class DeviceFullError(DeviceError):
    """
        raised when there is not enought free space for sending an object
    """
    pass

class AlreadyOnDeviceError(DeviceError):
    """
        raised when an object is already on the device
    """
    pass


class UnknowError(DeviceError):
    """
        raised when the device return an unidentified exception
    """
    pass


class DeviceEngine:

    def __init__(self, _device):
        self.__device = _device

    def connect_device(self):
        self.__device.connect()
        if DEBUG: debug_trace("Device connected successfully", sender=self)
        self.__object_listing_model = ObjectListingModel(self.__device)
        self.__container_tree_model = ContainerTreeModel(self.__device)

    def disconnect_device(self):
        self.__object_listing_model = None
        self.__container_tree_model = None
        self.__device.disconnect()

    def get_object_listing_model(self):
        return self.__object_listing_model

    def get_track_listing_model(self):
        return self.__object_listing_model.filter_tracks()

    def get_file_listing_model(self):
        return self.__object_listing_model

    def get_container_tree_model(self):
        return self.__container_tree_model

    def get_folder_tree_model(self):
        return self.__container_tree_model.filter_folders()

    def get_playlist_tree_model(self):
        return self.__container_tree_model.filter_playlists()

    def get_album_tree_model(self):
        return self.__container_tree_model.filter_albums()

    def send_file(self, metadata, callback):
        return self.__device.send_track(metadata, callback)

    def create_folder(self, metadata):
        return self.__device.create_folder(metadata)

    def del_file(self, file_id):
        return self.__device.remove_track(file_id)

    def get_device(self):
        return self.__device

class ObjectListingModel(gtk.ListStore):
    OBJECT_ID = 0
    PARENT_ID = 1
    TYPE = 2
    TITLE = 3
    ARTIST = 4
    ALBUM = 5
    GENRE = 6
    SIZE_STR = 7
    SIZE_INT = 8
    DATE_STR = 9
    DATE = 10
    ICON = 11
    METADATA = 12

    def __init__(self, _device):
        gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.__filter_tracks = self.filter_new()
        self.__filter_tracks.set_visible_func(self.__filter_type, Metadata.TYPE_TRACK)

        self.__cache = {}
        # lock to prevent more thread for uodating the model at the same time
        self.__lock = Lock()

        # add all tracks
        tracks_list = _device.get_tracklisting()
        for track_metadata in tracks_list:
            assert type(track_metadata) is type(Metadata.Metadata())
            self.append(track_metadata)

        # add other files (the ones which are not already registered as tracks)
        file_list = _device.get_filelisting()
        for file_metadata in file_list:
            assert type(file_metadata) is type(Metadata.Metadata())
            if not file_metadata.id in self.__cache.keys():
                self.append(file_metadata)

    def __filter_type(self, model, iter, type):
        return self.get_value(iter, self.TYPE) == type

    def filter_tracks(self):
        return self.__filter_tracks

    def __get_iter(self, object_id):
        try:
            return  self.get_iter(self.__cache[object_id].get_path())
        except KeyError, exc:
            return None

    def append(self, metadata):
        assert type(metadata) is type(Metadata.Metadata())
        m=metadata
        date_str=""
        if metadata.date:
            date_str = datetime.datetime.fromtimestamp(metadata.date).strftime('%a %d %b %Y')
        icon = "gtk-file"
        if Metadata.TYPE_TRACK:
            icon = "audio-x-generic"

        if DEBUG_LOCK: debug_trace(".append(): requesting lock (%s)" % m.id, sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace(".append(): lock acquired (%s)" % m.id, sender=self)

        row = [m.id, m.parent_id, m.type, m.title, m.artist, m.album, m.genre, util.format_filesize(m.filesize), m.filesize, date_str, m.date, icon, m]
        iter = gtk.ListStore.append(self, row)
        self.__cache[m.id] = gtk.TreeRowReference(self, self.get_path(iter))
        self.__lock.release()

        if DEBUG_LOCK: debug_trace(".append(): lock released (%s)" % m.id, sender=self)
        return iter

    def get_metadata(self, path):
        return self.get(self.get_iter(path), self.METADATA)[0]

    def remove_object(self, object_id):
        if DEBUG_LOCK: debug_trace(".remove_object(): requesting lock (%s)" % object_id, sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace(".remove_object(): lock acquired (%s)" % object_id, sender=self)
        it = self.__get_iter(object_id)
        if it:
            self.remove(it)
        else:
            debug_trace("trying to remove non existing object %s from model" % object_id, sender=self)
        self.__lock.release()
        if DEBUG_LOCK: debug_trace(".remove_object(): lock released (%s)" % object_id, sender=self)

class ContainerTreeModel(gtk.TreeStore):
    """ contains object parenting other object: folder, playlist or album """
    OBJECT_ID=0
    PARENT_ID=1
    NAME=2
    ICON=3
    METADATA=4

    def __init__(self, _device):
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING,
                    gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.__cache = {}
        # lock to prevent more thread for updating the model at the same time
        self.__lock = Lock()

        # add folder list
        #FIXME: sort item so that parent is alway created before its childs
        folder_list = _device.get_folder_list()
        for dir in folder_list:
            assert type(dir) is type(Metadata.Metadata())
            self.append(dir)

    def filter_folders(self):
        #TODO:
        return self

    def filter_playlists(self):
        #TODO:
        return self

    def filter_albums(self):
        #TODO:
        return self

    def __get_iter(self, object_id):
        try:
            return  self.get_iter(self.__cache[object_id].get_path())
        except KeyError, exc:
            return None

    def append(self, metadata):
        assert type(metadata) is type(Metadata.Metadata())
        m=metadata
        if DEBUG_LOCK: debug_trace(".append(): requesting lock (%s)" % m.id, sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace(".append(): lock acquired (%s)" % m.id, sender=self)
        parent=0
        if m.parent_id <> 0:
            parent = self.__get_iter(m.parent_id)

        row = [m.id, m.parent_id, m.title, "folder", m]

        iter = gtk.TreeStore.append(self, parent, row)
        self.__cache[m.id] = gtk.TreeRowReference(self, self.get_path(iter))
        self.__lock.release()
        if DEBUG_LOCK: debug_trace(".append(): lock released (%s)" % m.id, sender=self)
        return iter

    def get_metadata(self, path):
        return self.get(self.get_iter(path), self.METADATA)[0]

    def remove_object(self, object_id):
        if DEBUG_LOCK: debug_trace(".remove_object(): requesting lock (%s)" % object_id, sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace(".remove_object(): lock acquired (%s)" % object_id, sender=self)
        it = self.__get_iter(object_id)
        if it:
            self.remove(it)
        else:
            debug_trace("trying to remove non existing object %s from model" % object_id, sender=self)
        self.__lock.release()
        if DEBUG_LOCK: debug_trace(".remove_object(): lock released (%s)" % object_id, sender=self)
