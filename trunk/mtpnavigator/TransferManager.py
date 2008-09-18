import gtk
import gobject
from threading import Thread
from Queue import Queue
from urlparse import urlparse
from urllib import url2pathname
from DeviceEngine import DeviceEngine
from notifications import *
from time import sleep
import os
import Metadata
import util

class TransferManager():
    ACTION_SEND = 0
    ACTION_DEL = 1
    ACTION_GET = 2
    ACTION_CREATE_FOLDER = 3
    ACTION_CREATE_PLAYLIST = 4
    ACTION_ADD_TO_PLAYLIST = 5
    ACTION_REMOVE_FROM_PLAYLIST = 6
    ACTION_SEND_FILE_TO_PLAYLIST = 7
    icons={ ACTION_SEND: gtk.STOCK_GO_DOWN,
            ACTION_DEL: gtk.STOCK_DELETE,
            ACTION_GET: gtk.STOCK_GO_UP,
            ACTION_CREATE_FOLDER: gtk.STOCK_DIRECTORY,
            ACTION_CREATE_PLAYLIST: gtk.STOCK_EDIT,
            ACTION_ADD_TO_PLAYLIST: gtk.STOCK_ADD,
            ACTION_REMOVE_FROM_PLAYLIST: gtk.STOCK_REMOVE,
            ACTION_SEND_FILE_TO_PLAYLIST: gtk.STOCK_GO_DOWN
          }

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_ERROR = "error"

    def __init__(self, device_engine, transfer_treeview, notebook, disk_usage_progress_bar):
        self.__queue = Queue()
        self.__device_engine = device_engine

        self.__model = TransfertQueueModel()

        process_queue_thread = ProcessQueueThread(device_engine, self, self.__queue, self.__model)
        process_queue_thread.add_observer(self.__observe_queue_thread)
        process_queue_thread.setDaemon(True)
        gtk.gdk.threads_enter()
        process_queue_thread.start()
        gtk.gdk.threads_leave()
        self.__transfer_treeview = transfer_treeview
        self.__notebook = notebook
        self.__disk_usage_progress_bar = disk_usage_progress_bar

        t=TransfertQueueModel
        if False:
            col = gtk.TreeViewColumn("object_id", gtk.CellRendererText(), text=t.COL_JOB_ID)
            transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("action", gtk.CellRendererPixbuf (), stock_id=t.COL_ACTION_STOCK)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("description", gtk.CellRendererText(), text=t.COL_DESCRIPTION)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("progress", gtk.CellRendererProgress(), value=t.COL_PROGRESS, text=t.COL_STATUS)
        transfer_treeview.append_column(col)
        transfer_treeview.set_model(self.__model)
        transfer_treeview.get_selection().set_mode( gtk.SELECTION_MULTIPLE)

    def __observe_queue_thread(self, signal, *args):
        if signal == ProcessQueueThread.SIGNAL_DEVICE_CONTENT_CHANGED:
            gobject.idle_add(self.__disk_usage_progress_bar.set_fraction, float(args[1])/float(args[2]))
            gobject.idle_add(self.__disk_usage_progress_bar.set_text, "%s of %s" % (util.format_filesize(args[1]), util.format_filesize(args[2])))
            if DEBUG: debug_trace("notified SIGNAL_DEVICE_CONTENT_CHANGED", sender=self)
            job = args[0]
            if job.action==self.ACTION_SEND:
                gobject.idle_add(self.__device_engine.get_object_listing_model().append, job.metadata)
            elif job.action==self.ACTION_DEL:
                if job.metadata.type == Metadata.TYPE_FOLDER:
                    gobject.idle_add(self.__device_engine.get_folder_tree_model().remove_object, job.metadata.id)
                elif job.metadata.type == Metadata.TYPE_PLAYLIST:
                    gobject.idle_add(self.__device_engine.get_playlist_tree_model().remove_object, job.metadata.id)
                elif job.metadata.type == Metadata.TYPE_TRACK:
                    gobject.idle_add(self.__device_engine.get_object_listing_model().remove_object, job.metadata.id)
                    # also try to remove from playlist model if the track belogn a playlist
                    gobject.idle_add(self.__device_engine.get_playlist_tree_model().remove_object, job.metadata.id)
                else:
                   gobject.idle_add(self.__device_engine.get_object_listing_model().remove_object, job.metadata.id)
            elif job.action==self.ACTION_CREATE_FOLDER:
                gobject.idle_add(self.__device_engine.get_folder_tree_model().append, job.metadata)
            elif job.action==self.ACTION_CREATE_PLAYLIST:
                gobject.idle_add(self.__device_engine.get_playlist_tree_model().append, job.metadata)
            elif job.action==self.ACTION_REMOVE_FROM_PLAYLIST:
                gobject.idle_add(self.__device_engine.get_playlist_tree_model().remove_object, job.metadata.id)
            elif job.action==self.ACTION_ADD_TO_PLAYLIST:
                gobject.idle_add(self.__device_engine.get_playlist_tree_model().append, job.metadata)
            elif job.action==self.ACTION_SEND_FILE_TO_PLAYLIST:
                gobject.idle_add(self.__device_engine.get_object_listing_model().append, job.metadata)
                gobject.idle_add(self.__device_engine.get_playlist_tree_model().append, job.metadata)

    def __queue_job(self, job_type, metadata):
        assert type(metadata) is type(Metadata.Metadata())
        job = Job(metadata.id, job_type, self.STATUS_QUEUED, metadata)

        self.__queue.put_nowait(job)
        self.__model.append(job.get_list())

        trace("queued file %s for %s" % (job.object_id, job.action), sender=self)
        self.__notebook.set_current_page(1)

    def get_selection(self):
        return self.__transfer_treeview.get_selection()

    def create_folder(self, folder_name, parent_id):
        metadata = Metadata.Metadata()
        metadata.id = folder_name
        metadata.title = folder_name
        metadata.filename = folder_name
        metadata.parent_id = parent_id
        metadata.type = Metadata.TYPE_FOLDER
        self.__queue_job(self.ACTION_CREATE_FOLDER, metadata)

    def create_playlist(self, playlist_name):
        metadata = Metadata.Metadata()
        metadata.id = playlist_name
        metadata.title = playlist_name
        metadata.filename = playlist_name
        metadata.parent_id = 0
        metadata.type = Metadata.TYPE_PLAYLIST
        self.__queue_job(self.ACTION_CREATE_PLAYLIST, metadata)

    def add_track_to_playlist(self, play_list_id, track, next_track):
        if DEBUG: debug_trace("request for adding %s to playlist %s" % (track.title, play_list_id), sender=self)
        #TODO: handle next_track in job
        track.parent_id = play_list_id
        track.next_object = next_track
        self.__queue_job(self.ACTION_ADD_TO_PLAYLIST, track)

    def remove_track_from_playlist(self, playlist_item_metadata):
        if DEBUG: debug_trace("request for removing %s from playlist %s" % (playlist_item_metadata.title, playlist_item_metadata.parent_id), sender=self)
        self.__queue_job(self.ACTION_REMOVE_FROM_PLAYLIST, playlist_item_metadata)

    def __convert_file_url_to_metadata(self, file_url):
        url = urlparse(file_url)
        if url.scheme == "file":
            path = url2pathname(url.path)
            metadata = Metadata.get_from_file(path)
            return metadata
        else:
            notify_warning("%s is not a file" % file_url)
            return None

    def send_extern_file_to_playlist(self, play_list_id, file_url, next_track):
        """
            send an extern file to the device then add it to the playlist
            in one operation. Because the new object_id is needed to update the playlits
        """
        if DEBUG: debug_trace("request for sending extern file %s to playlist %s" % (file_url, play_list_id), sender=self)
        metadata = self.__convert_file_url_to_metadata(file_url)
        metadata.parent_id = play_list_id
        metadata.next_object = next_track
        if metadata:
            self.__queue_job(self.ACTION_SEND_FILE_TO_PLAYLIST, metadata)

    def send_file(self, file_url, parent_id):
        if DEBUG: debug_trace("request for sending %s to parent %s" % (file_url, parent_id), sender=self)
        metadata = self.__convert_file_url_to_metadata(file_url)
        metadata.parent_id = parent_id
        if metadata:
            self.__queue_job(self.ACTION_SEND, metadata)

    def del_file(self, metadata):
        if DEBUG: debug_trace("request for deleting file with id %s (%s)" % (metadata.id, metadata.filename), sender=self)
        self.__queue_job(self.ACTION_DEL, metadata)

    def cancel_job(self, job_to_cancel):
        job_to_cancel.canceled = True
        self.__model.remove_job(job_to_cancel.object_id) #FIXME: not for current job

class ProcessQueueThread(Thread):
    SIGNAL_QUEUE_CHANGED = 1
    SIGNAL_DEVICE_CONTENT_CHANGED = 2

    def __init__(self, device_engine, transfer_manager, _queue, model):
        self.__device_engine = device_engine
        self.__queue = _queue
        self.__model = model
        self.__current_job = None
        Thread.__init__(self)
        self.observers = []

    def __notify(self, signal, *args):
        for observer in self.observers:
            observer(signal, *args)

    def __device_callback(self, sent, total):
        if self.__current_job.canceled:
            debug_trace("current job canceled", sender=self)
            return 1
        percentage = round(float(sent)/float(total)*100)
        self.__current_job.progress=percentage
        self.__model.modify(self.__current_job.object_id, TransfertQueueModel.COL_PROGRESS, percentage)
        self.__model.modify(self.__current_job.object_id, TransfertQueueModel.COL_STATUS, "%i%%" % percentage)
        return 0

    def add_observer(self, observer):
        if DEBUG and observer in self.observers:
            debug_trace("observer already registered to transfer manager", sender=self)
        else:
            self.observers.append(observer)

    def run(self):
        if DEBUG: debug_trace("Processing queue thread started ", sender=self)
        while(True):
            job = self.__queue.get() # will wait until an job is there
            if job.canceled: continue
            self.__current_job = job
            self.__model.modify(job.object_id, TransfertQueueModel.COL_STATUS, TransferManager.STATUS_PROCESSING)
            debug_trace("Processing job %s" % job.object_id, sender=self)
            try:
                previous_id=job.object_id
                if job.action == TransferManager.ACTION_SEND:
                    metadata = self.__device_engine.send_file(job.metadata, self.__device_callback)
                    trace("%s sent successfully. New id is %s" % (job.object_id, metadata.id), sender=self)
                    job.object_id = metadata.id
                    job.metadata = metadata
                    self.__model.modify(job.object_id, TransfertQueueModel.COL_JOB_ID, id)

                elif job.action == TransferManager.ACTION_DEL:
                    self.__device_engine.del_file(job.object_id)
                    trace("file with id %s (%s) deleted succesfully" % (job.object_id, job.metadata.title), sender=self)

                elif job.action == TransferManager.ACTION_CREATE_FOLDER:
                    metadata = self.__device_engine.create_folder(job.metadata)
                    trace("New folder %s created succesfully. New id is %s" % (job.object_id, metadata.id), sender=self)
                    job.object_id = metadata.id
                    job.metadata = metadata
                    self.__model.modify(job.object_id, TransfertQueueModel.COL_JOB_ID, id)

                elif job.action == TransferManager.ACTION_CREATE_PLAYLIST:
                    metadata = self.__device_engine.create_playlist(job.metadata)
                    trace("New playlist %s created succesfully. New id is %s" % (job.object_id, metadata.id), sender=self)
                    job.object_id = metadata.id
                    job.metadata = metadata
                    self.__model.modify(job.object_id, TransfertQueueModel.COL_JOB_ID, id)

                elif job.action == TransferManager.ACTION_ADD_TO_PLAYLIST:
                    self.__device_engine.add_track_to_playlist(job.metadata)
                    trace("Track %s successfully added to playlist %s" % (job.metadata.title, job.metadata.parent_id), sender=self)

                elif job.action == TransferManager.ACTION_SEND_FILE_TO_PLAYLIST:
                    (metadata, playlist_id) = self.__device_engine.send_file_to_playlist(job.metadata, self.__device_callback)
                    trace("Track %s successfully sent and added to playlist %s" % (job.metadata.title, job.metadata.parent_id), sender=self)
                    job.object_id = metadata.id
                    job.metadata = metadata
                    self.__model.modify(job.object_id, TransfertQueueModel.COL_JOB_ID, id)
                    # FIXME: find a way to pass playlist_id for refreshing playlist model

                elif job.action == TransferManager.ACTION_REMOVE_FROM_PLAYLIST:
                    self.__device_engine.remove_track_from_playlist(job.metadata)
                    trace("Track %s successfully removed from playlist %s" % (job.metadata.title, job.metadata.parent_id), sender=self)

                else:
                    if DEBUG: debug_trace("Unknow action: %i" % job.action, sender=self)
                    assert False
                disque_usage = self.__device_engine.get_device().get_diskusage()
                self.__notify(self.SIGNAL_DEVICE_CONTENT_CHANGED, job, disque_usage[0], disque_usage[1])
                self.__model.remove_job(previous_id)
            except Exception, exc:
                if DEBUG: debug_trace("Failed to process %s" % job.object_id , sender=self, exception=exc)
                job.status = TransferManager.STATUS_ERROR
                job.exception = exc
                self.__model.modify(job.object_id, TransfertQueueModel.COL_STATUS, TransferManager.STATUS_ERROR + ': ' + str(exc))
            finally:
                self.__current_job = None

class TransfertQueueModel(gtk.ListStore):
    COL_JOB_ID=0
    COL_ACTION=1
    COL_ACTION_STOCK=2
    COL_DESCRIPTION=3
    COL_STATUS=4
    COL_PROGRESS=5
    COL_JOB=6

    def __init__(self):
        gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_FLOAT, gobject.TYPE_PYOBJECT)

    def __get_iter(self, job_id):
        iter = None
        iter = self.get_iter_first()
        while iter:
            if self.get(iter, self.COL_JOB_ID)[0] == job_id:
                break
            iter = self.iter_next(iter)
        return iter

    def append(self, track):
        iter = gtk.ListStore.append(self, track)
        return iter

    def get_job(self, path):
        return self.get(self.get_iter(path), self.COL_JOB)[0]

    def remove_job(self, object_id):
        it = self.__get_iter(object_id)
        if it:
            self.remove(it)
        else:
            debug_trace("trying to remove non existing object %s from model" % object_id, sender=self)

    def modify(self, object_id, column, value):
        it = self.__get_iter(object_id)
        if it:
            self.set_value(it, column, value)
            if column==self.COL_ACTION:
                self.set_value(it, self.COL_ACTION_STOCK, TransferManager.icons(value))
        else:
            debug_trace("trying to update non existing object %s from model" % object_id, sender=self)

class Job():
    def __init__(self, object_id, action, status, metadata):
        assert type(metadata) is type(Metadata.Metadata())
        self.object_id = object_id
        self.action = action
        self.status = status
        self.exception = None
        self.progress = 0
        self.metadata = metadata
        self.canceled = False

    def get_list(self):
        """
            return a list of attributes. needed for model
        """
        return [self.object_id, self.action, TransferManager.icons[self.action], self.metadata.title, self.status, self.progress, self]