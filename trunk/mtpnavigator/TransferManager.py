import gtk
import gobject
from threading import Thread
from urlparse import urlparse
from DeviceEngine import DeviceEngine
from notifications import *

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
        self.__queue = []
        self.__error_queue = []
        self.__device_engine = device_engine
        process_queue_thread = ProcessQueueThread(device_engine, self, self.__queue, self.__error_queue)
        process_queue_thread.add_observer(self.__observe_queue_thread)
        process_queue_thread.setDaemon(True)
        process_queue_thread.start()
        self.__transfer_treeview = transfer_treeview
        self.__notebook = notebook

        #col = gtk.TreeViewColumn("object_id", gtk.CellRendererText(), text=0)
        #transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("action", gtk.CellRendererText(), text=1)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("description", gtk.CellRendererText(), text=2)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("status", gtk.CellRendererText(), text=3)
        transfer_treeview.append_column(col)

        self.__model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        transfer_treeview.set_model(self.__model)

    def __observe_queue_thread(self, signal, *args):
        if signal == ProcessQueueThread.SIGNAL_QUEUE_CHANGED:
            if DEBUG: debug_trace("notified SIGNAL_QUEUE_CHANGED", sender=self)
            self.__update_model()
        elif signal == ProcessQueueThread.SIGNAL_DEVICE_CONTENT_CHANGED:
            if DEBUG: debug_trace("notified SIGNAL_DEVICE_CONTENT_CHANGED", sender=self)
            self.__device_engine.update_models()

    def __update_model(self):
        if DEBUG: debug_trace("Updating model.", sender=self)
        self.__model.clear()
        for job in self.__queue.join(self.__error_queue):
            status = job.status
            if status==self.STATUS_PROCESSING:
                status += " %i%%" % job.progress
            self.__model.append([job.object_id, job.action, job.description, job.status])

    def __queue_job(self, object_id, job_type, description):
        job = Job(object_id, job_type, self.STATUS_QUEUED, description)

        if self.__queue.count(job) > 0: # FIXME: check ignoring the status
            warning_trace("%s already in queue" % file_url, sender=self)
            return

        self.__queue.append(job)
        self.__model.append([job.object_id, job.action, job.description, job.status])

        trace("queued file %s for %s" % (job.object_id, job.action), sender=self)
        self.__notebook.set_current_page(1)

    def send_file(self, file_url):
        if DEBUG: debug_trace("request for sending %s" % file_url, sender=self)
        url = urlparse(file_url)
        if url.scheme == "file":
            self.__queue_job(url.path, self.ACTION_SEND, url.path)
        else:
            warning_trace("%s is not a file" % file_url, sender=self)

    def del_file(self, file_id, file_description):
        if DEBUG: debug_trace("request for deleting file with id %s (%s)" % (file_id, file_description), sender=self)
        self.__queue_job(file_id, self.ACTION_DEL, file_description)

class ProcessQueueThread(Thread):
    SIGNAL_QUEUE_CHANGED = 1
    SIGNAL_DEVICE_CONTENT_CHANGED = 2

    def __init__(self, device_engine, transfer_manager, _queue):
        self.__device_engine = device_engine
        self.__queue = _queue
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
            if len(self.__queue) > 0:
                job = self.__queue.pop()
                self.__current_job = job
                job.status = TransferManager.STATUS_PROCESSING
                self.__notify(self.SIGNAL_QUEUE_CHANGED)
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
                    self.__error.append(job)
                finally:
                    self.__current_job = None
                    self.__notify(self.SIGNAL_QUEUE_CHANGED)

class Job():
    def __init__(self, object_id, action, status, description):
        self.object_id = object_id
        self.action = action
        self.status = status
        self.description = description
        self.exception = None
        self.progress = 0
