import gtk
import gobject
from threading import thread
from Queue import Queue 
from urlparse import urlparse
from urllib import url2pathname
from DeviceEngine import DeviceEngine
from notifications import *
from time import sleep

class TransferManager():
    ACTION_SEND = "sending"
    ACTION_DEL = "deleting"
    ACTION_GET = "getting"
    ACTION_CREATE_DIR = "creating directory"
    ACTION_DEL_DIR = "deleleting directory"
    ACTION_CREATE_PLAYLIST = "creating playlist"
    ACTION_DEL_PLAYLIST = "deleting playlist"

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_ERROR = "blocked on error"

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

        if DEBUG:
            col = gtk.TreeViewColumn("object_id", gtk.CellRendererText(), text=0)
            transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("action", gtk.CellRendererText(), text=1)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("description", gtk.CellRendererText(), text=2)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("status", gtk.CellRendererText(), text=3)
        transfer_treeview.append_column(col)
        transfer_treeview.set_model(self.__model)

    def __observe_queue_thread(self, signal, *args):
        if signal == ProcessQueueThread.SIGNAL_DEVICE_CONTENT_CHANGED:
            if DEBUG: debug_trace("notified SIGNAL_DEVICE_CONTENT_CHANGED", sender=self)
            self.__device_engine.update_models()

    def __queue_job(self, object_id, job_type, description):
        job = Job(object_id, job_type, self.STATUS_QUEUED, description)

        self.__queue.put_nowait(job)
        self.__model.append([job.object_id, job.action, job.description, job.status])

        trace("queued file %s for %s" % (job.object_id, job.action), sender=self)
        self.__notebook.set_current_page(1)

    def send_file(self, file_url):
        if DEBUG: debug_trace("request for sending %s" % file_url, sender=self)
        url = urlparse(file_url)
        if url.scheme == "file":
            path = url2pathname(url.path)
            self.__queue_job(path, self.ACTION_SEND, path)
        else:
            warning_trace("%s is not a file" % file_url, sender=self)

    def del_file(self, file_id, file_description):
        if DEBUG: debug_trace("request for deleting file with id %s (%s)" % (file_id, file_description), sender=self)
        self.__queue_job(file_id, self.ACTION_DEL, file_description)

class ProcessQueueThread(Thread):
    SIGNAL_QUEUE_CHANGED = 1
    SIGNAL_DEVICE_CONTENT_CHANGED = 2

    def __init__(self, device_engine, transfer_manager, _queue, model):
        self.__device_engine = device_engine
        self.__queue = _queue
        self.__errors
        self.__current_job = None
        Thread.__init__(self)
        self.observers = []

    def __notify(self, signal, *args):
        for observer in self.observers:
            observer(signal, *args)

    def __device_callback(self, sent, total):
        percentage = round(float(sent)/float(total)*100)
        self.__current_job.progress=percentage
        #FIXME: self.__notify(self.SIGNAL_QUEUE_CHANGED)

    def add_observer(self, observer):
        if DEBUG and observer in self.observers:
            debug_trace("observer already registered to transfer manager", sender=self)
        else:
            self.observers.append(observer)

    def run(self):
        if DEBUG: debug_trace("Processing queue thread started ", sender=self)
        while(True):
            job = self.__queue.get() # will wait until an job is there
            #todo: remove from model
            self.__current_job = job
            job.status = TransferManager.STATUS_PROCESSING
            #self.__model.remove_job(job) #FIXME: needed to refresh?
            #self.__model.append(job)
            debug_trace("Processing job %s" % job.object_id, sender=self)
            try:
                if job.action == TransferManager.ACTION_SEND:
                    self.__device_engine.send_file(job.object_id, self.__device_callback)
                    trace("%s sent successfully" % job.object_id, sender=self)
                elif job.action == TransferManager.ACTION_DEL:
                    self.__device_engine.del_file(job.object_id)
                    trace("file with id %s deleted succesfully" % job.object_id, sender=self)
                else:
                    assert False
                self.__notify(self.SIGNAL_DEVICE_CONTENT_CHANGED)
            except Exception, exc:
                if DEBUG: debug_trace("Failed to process %s" % job.object_id , sender=self, exception=exc)
                job.status = TransferManager.STATUS_ERROR
                job.exception = exc
                self.__model.append(job)
            finally:
                self.__model.remove_job(job) #FIXME: needed to refresh?
                self.__current_job = None

class TransfertQueueModel(gtk.ListStore)
    self.COL_JOB_ID=0
    
    def __init__(self):
        gtk.ListStore.__init__(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
    
    def __get_iter(self, object_id):
        #FIXME: use treeiter and if to cache rows?
        it = self.get_iter_first()
        while it
            if self.get_value(it, self.self.COL_JOB_ID) == object_id:
                return it
            it = self.iter_next()
        return None        
        
    def remove_job(self, job):
        it = __get_row_iter(job.object_id)
        if it:
            self.remove(it)
        else:
            notify_warning("trying to remove non existing object %s from model", job.object_id)

class Job():
    def __init__(self, object_id, action, status, description):
        self.object_id = object_id
        self.action = action
        self.status = status
        self.description = description
        self.exception = None
        self.progress = 0
