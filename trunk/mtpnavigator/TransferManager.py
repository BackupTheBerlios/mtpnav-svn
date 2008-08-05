import gtk
import gobject
from threading import Thread
from threading import Lock
from Queue import Queue
from urlparse import urlparse
from urllib import url2pathname
from DeviceEngine import DeviceEngine
from notifications import *
from time import sleep
import os
import Metadata

class TransferManager():
    ACTION_SEND = "SEND"
    ACTION_DEL = "DELETE"
    ACTION_GET = "GET"
    ACTION_CREATE_DIR = "creating directory"
    ACTION_DEL_DIR = "deleleting directory"
    ACTION_CREATE_PLAYLIST = "creating playlist"
    ACTION_DEL_PLAYLIST = "deleting playlist"

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_ERROR = "error"

    def __init__(self, device_engine, transfer_treeview, notebook):
        self.__queue = Queue()
        self.__device_engine = device_engine

        self.__model = TransfertQueueModel()

        process_queue_thread = ProcessQueueThread(device_engine, self, self.__queue, self.__model)
        process_queue_thread.add_observer(self.__observe_queue_thread)
        process_queue_thread.setDaemon(True)
        process_queue_thread.start()
        self.__transfer_treeview = transfer_treeview
        self.__notebook = notebook

        t=TransfertQueueModel
        if False:
            col = gtk.TreeViewColumn("object_id", gtk.CellRendererText(), text=t.COL_JOB_ID)
            transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("action", gtk.CellRendererText(), text=t.COL_ACTION)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("description", gtk.CellRendererText(), text=t.COL_DESCRIPTION)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("progress", gtk.CellRendererProgress(), value=t.COL_PROGRESS, text=t.COL_STATUS)
        transfer_treeview.append_column(col)
        transfer_treeview.set_model(self.__model)

    def __observe_queue_thread(self, signal, *args):
        if signal == ProcessQueueThread.SIGNAL_DEVICE_CONTENT_CHANGED:
            if DEBUG: debug_trace("notified SIGNAL_DEVICE_CONTENT_CHANGED", sender=self)
            job = args[0]
            if job.action==self.ACTION_SEND:
                self.__device_engine.get_track_listing_model().append(job.metadata)
                self.__device_engine.get_file_tree_model().append(job.metadata)
            elif job.action==self.ACTION_DEL:
                self.__device_engine.get_track_listing_model().remove_object(job.metadata.id)
                self.__device_engine.get_file_tree_model().remove_object(job.metadata.id)

    def __queue_job(self, object_id, job_type, metadata):
        assert type(metadata) is type(Metadata.Metadata())
        job = Job(object_id, job_type, self.STATUS_QUEUED, metadata)

        self.__queue.put_nowait(job)
        self.__model.append(job.get_list())

        trace("queued file %s for %s" % (job.object_id, job.action), sender=self)
        self.__notebook.set_current_page(1)

    def get_selection(self):
        return self.__transfer_treeview.get_selection()

    def send_file(self, file_url):
        if DEBUG: debug_trace("request for sending %s" % file_url, sender=self)
        url = urlparse(file_url)
        if url.scheme == "file":
            path = url2pathname(url.path)
            metadata = Metadata.get_from_file(path)
            self.__queue_job(path, self.ACTION_SEND, metadata)
        else:
            notify_warning("%s is not a file" % file_url)

    def del_file(self, metadata):
        if DEBUG: debug_trace("request for deleting file with id %s (%s)" % (metadata.id, metadata.filename), sender=self)
        self.__queue_job(metadata.id, self.ACTION_DEL, metadata)

    def cancel_job(self, job_to_cancel):
        job_to_cancel.canceled = True
        self.__model.remove_job(job_to_cancel.id) # FIXME: not for current job

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
        percentage = round(float(sent)/float(total)*100)
        self.__current_job.progress=percentage
        self.__model.modify(self.__current_job.object_id, TransfertQueueModel.COL_PROGRESS, percentage)
        self.__model.modify(self.__current_job.object_id, TransfertQueueModel.COL_STATUS, "%i%%" % percentage)
        if self.__current_job.canceled: 
            debug_trace("current job canceled", sender=self)
            return 1

    def add_observer(self, observer):
        if DEBUG and observer in self.observers:
            debug_trace("observer already registered to transfer manager", sender=self)
        else:
            self.observers.append(observer)

    def run(self):
        if DEBUG: debug_trace("Processing queue thread started ", sender=self)
        while(True):
            job = self.__queue.get() # will wait until an job is there
            if job.canceled: break
            self.__current_job = job
            self.__model.modify(job.object_id, TransfertQueueModel.COL_STATUS, TransferManager.STATUS_PROCESSING)
            debug_trace("Processing job %s" % job.object_id, sender=self)
            try:
                previous_id=job.object_id
                if job.action == TransferManager.ACTION_SEND:
                    metadata = self.__device_engine.send_file(job.metadata, self.__device_callback)
                    trace("%s sent successfully. New id is %s" % (job.object_id, metadata.id), sender=self)
                    self.__model.modify(job.object_id, TransfertQueueModel.COL_JOB_ID, id)
                    job.object_id = metadata.id
                    job.metadata = metadata
                elif job.action == TransferManager.ACTION_DEL:
                    self.__device_engine.del_file(job.object_id)
                    trace("file with id %s (%s) deleted succesfully" % (job.object_id, job.metadata.title), sender=self)
                else:
                    assert False
                self.__notify(self.SIGNAL_DEVICE_CONTENT_CHANGED, job)
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
    COL_DESCRIPTION=2
    COL_STATUS=3
    COL_PROGRESS=4
    COL_JOB=5

    def __init__(self):
        gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_FLOAT, gobject.TYPE_PYOBJECT)
        self.__cache = {}
        # lock to prevent more thread for updating the model at the same time
        self.__lock = Lock()

    def __get_iter(self, object_id):
        try:
            return  self.get_iter(self.__cache[object_id].get_path())
        except KeyError, exc:
            return None

    def append(self, track):
        if DEBUG_LOCK: debug_trace("Requesting lock", sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace("Lock acquired", sender=self)
        iter = gtk.ListStore.append(self, track)
        self.__cache[track[0]] = gtk.TreeRowReference(self, self.get_path(iter))
        self.__lock.release()
        if DEBUG_LOCK: debug_trace("Lock released", sender=self)
        return iter

    def get_job(self, path):
        return self.get(self.get_iter(path), self.COL_JOB)[0]

    def remove_job(self, object_id):
        if DEBUG_LOCK: debug_trace("Requesting lock", sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace("Lock acquired", sender=self)
        it = self.__get_iter(object_id)
        if it:
            self.remove(it)
        else:
            debug_trace("trying to remove non existing object %s from model" % object_id, sender=self)
        self.__lock.release()
        if DEBUG_LOCK: debug_trace("Lock released", sender=self)

    def modify(self, object_id, column, value):
        if DEBUG_LOCK: debug_trace("Requesting lock", sender=self)
        self.__lock.acquire()
        if DEBUG_LOCK: debug_trace("Lock acquired", sender=self)
        it = self.__get_iter(object_id)
        if it:
            self.set_value(it, column, value)
        else:
            debug_trace("trying to update non existing object %s from model" % object_id, sender=self)
        self.__lock.release()
        if DEBUG_LOCK: debug_trace("Lock released", sender=self)

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
        return [self.object_id, self.action, self.metadata.title, self.status, self.progress, self]