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
        self.__track_listing_model = TrackListingModel(self.__device)
        self.__file_tree_model = FileTreeModel(self.__device)

    def disconnect_device(self):
        self.__track_listing_model = None
        self.__file_tree_model = None
        self.__device.disconnect()

    def get_track_listing_model(self):
        return self.__track_listing_model

    def get_file_tree_model(self):
        return self.__file_tree_model

    def send_file(self, metadata, callback):
        return self.__device.send_track(metadata, callback)

    def create_folder(self, metadata):
        return self.__device.create_folder(metadata)

    def del_file(self, file_id):
        return self.__device.remove_track(file_id)

    def get_device(self):
        return self.__device

class TrackListingModel(gtk.ListStore):
    OBJECT_ID=0
    PARENT_ID=1
    TITLE=2
    ARTIST=3
    ALBUM=4
    GENRE=5
    LENGTH_STR=6
    LENGTH_INT=7
    DATE_STR=8
    DATE=9
    METADATA=10

    def __init__(self, _device):
        gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.__cache = {}
        # lock to prevent more thread for uodating the model at the same time
        self.__lock = Lock()

        tracks_list = _device.get_tracklisting()
        for track_metadata in tracks_list:
            assert type(track_metadata) is type(Metadata.Metadata())
            self.append(track_metadata)

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
        if DEBUG_LOCK: debug_trace(".append(): requesting lock (%s)" % m.id, sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace(".append(): lock acquired (%s)" % m.id, sender=self)
        iter = gtk.ListStore.append(self, [m.id, m.parent_id, m.title, m.artist, m.album, m.genre, util.format_filesize(m.filesize), m.filesize, date_str, m.date, m])
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

class FileTreeModel(gtk.TreeStore):
    OBJECT_ID=0
    PARENT_ID=1
    FILENAME=2
    LENGTH_STR=3
    LENGTH_INT=4
    ICON=5
    METADATA=6

    def __init__(self, _device):
        gtk.TreeStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT, gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.__cache = {}
        # lock to prevent more thread for updating the model at the same time
        self.__lock = Lock()

        # add folder list
        #FIXME: sort item so that parent is alway created before its childs
        folder_list = _device.get_folder_list()
        for dir in folder_list:
            assert type(dir) is type(Metadata.Metadata())
            self.append(dir)

        # add file list
        file_list = _device.get_filelisting()
        for file_metadata in file_list:
            assert type(file_metadata) is type(Metadata.Metadata())
            self.append(file_metadata)

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

        if m.type == Metadata.TYPE_FOLDER:
            row = [m.id, m.parent_id, m.title, "", 0, "folder", m]
        else:
            icon = "gtk-file"
            if Metadata.TYPE_TRACK:
                icon = "audio-x-generic"
            row = [m.id, m.parent_id, m.title, util.format_filesize(m.filesize), m.filesize, icon, m]

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


