import gtk
import threading
import gobject
from urlparse import urlparse
from DeviceEngine import DeviceEngine
from notifications import *

class TransferManager():
    ACTION_SEND = "sending"
    ACTION_DEL = "deleting"
    ACTION_GET = "getting"
    ACTION_CREATE_DIR = "creating directory"
    ACTION_DEL_DIR = "deleltin directory"
    ACTION_CREATE_PLAYLIST = "creating playlist"
    ACTION_DEL_PLAYLIST = "deleting playlist"

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_ERROR = "blocked on error"

    def __init__(self, device_engine, transfer_treeview):
        self.__queue = []
        self.__failed_job = []
        self.__device_engine = device_engine
        self.__process_queue_thread = ProcessQueueThread(device_engine, self, self.__queue)

        self.__transfer_treeview = transfer_treeview
        col = gtk.TreeViewColumn("object_id", gtk.CellRendererText(), text=0)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("action", gtk.CellRendererText(), text=1)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("description", gtk.CellRendererText(), text=2)
        transfer_treeview.append_column(col)
        col = gtk.TreeViewColumn("status", gtk.CellRendererText(), text=3)
        transfer_treeview.append_column(col)

        self.__model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        transfer_treeview.set_model(self.__model)

    def update_model(self):
        debug_trace("Updating model.", sender=self)
        self.__model.clear()
        for job in self.__queue:
            self.__model.append([job.object_id, job.action, job.description, job.status])

    def __queue_job(self, object_id, job_type, description):
        job = Job(object_id, job_type, self.STATUS_QUEUED, description)

        if self.__queue.count(job) > 0: # FIXME: check ignoring the status
            warning_trace("%s already in queue" % file_url, sender=self)
            return

        self.__queue.append(job)
        trace("queued file %s for %s" % (job.object_id, job.action), sender=self)

        self.update_model()

        # process the queue if not active
        if not self.__process_queue_thread.isAlive():
            self.__process_queue_thread.run()

    def send_file(self, file_url):
        debug_trace("request for sending %s" % file_url, sender=self)
        url = urlparse(file_url)
        if url.scheme == "file":
            self.__queue_job(url.path, self.ACTION_SEND, url.path)
        else:
            warning_trace("%s is not a file" % file_url, sender=self)

    def del_file(self, file_id, file_description):
        debug_trace("request for deleting %s" % file_url, sender=self)
        self.__queue_job(file_id, self.ACTION_DEL, file_description)

class ProcessQueueThread(threading.Thread):
    def __init__(self, device_engine, transfer_manager, _queue):
        self.__device_engine = device_engine
        self.__transfer_manager = transfer_manager #FIXME: remove when not needed anymore
        self.__queue = _queue
        threading.Thread.__init__(self)

    def __device_callback(self, sent, total):
        percentage = round(float(sent)/float(total)*100)
        text = ('%i%%' % percentage)
        print text
        while gtk.events_pending():
            gtk.main_iteration(False)

    def run(self):
        debug_trace("Processing queue thread started ", sender=self)
        while len(self.__queue) > 0: #FIXME: count only status queued
            job = self.__queue[0]
            job.status = self.__transfer_manager.STATUS_PROCESSING
            #TODO debug_trace("Processing " + job, sender=self)
            try:
                if job.action == self.__transfer_manager.ACTION_SEND:
                    self.__device_engine.send_file(job.object_id, self.__device_callback) #TODO: callback
                    trace("%s sent succesfully" % job.object_id, sender=self)
                if job.action == self.__transfer_manager.ACTION_DEL:
                    self.__device_engine.del_file(job.object_id)
                    trace("file with id %s deleted succesfully" % job.object_id, sender=self)
                self.__queue.remove(job)
                #FIXME implements observer/observable pattern instead of using gui itself
                gtk.gdk.threads_enter()
                self.__device_engine.update_models()
                gtk.gdk.threads_leave()
            except Exception, exc:
                debug_trace("Failed to process " + job.object_id , sender=self, exception=exc)
                job.status = self.__transfer_manager.STATUS_ERROR
                job.exception = exc
            finally:
                #FIXME implements observer/observable pattern instead of using gui itself
                gtk.gdk.threads_enter()
                self.__transfer_manager.update_model()
                gtk.gdk.threads_leave()
        debug_trace("Processing queue thread finished", sender=self)

class Job():
    def __init__(self, object_id, action, status, description):
        self.object_id = object_id
        self.action = action
        self.status = status
        self.description = description
        self.exception = None
