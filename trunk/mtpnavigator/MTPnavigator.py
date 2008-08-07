#!/usr/bin/env python
import pygtk
pygtk.require("2.0")
import gtk
from DeviceEngine import DeviceEngine
from mtpDevice import MTPDevice
from TransferManager import TransferManager
from notifications import *
from DeviceEngine import TrackListingModel
from DeviceEngine import FileTreeModel
import util
import Metadata

VERSION="0.1.a2"

class MTPnavigator:
    def __init__(self):
        self.__treeview_track = None
        self.__treeview_file = None
        self.__device_engine = None
        self.__transferManager = None

        # bind to glade
        self.gtkbuilder = gtk.Builder()
        self.gtkbuilder.add_from_file("./mtpnavigator/MTPnavigator.xml")
        self.gtkbuilder.connect_signals(self)
        self.window = self.__getWidget("window_mtpnav")
        wwidth=800  #TODO save size
        wheight=600
        self.window.set_default_size(wwidth, wheight)
        self.window.set_size_request(500,350)
        self.window.set_title("MTP navigatore " + VERSION)
        self.__getWidget("vpaned_main").set_position(wheight-250) #TODO: save position

        # create the track view
        self.__treeview_track = self.gtkbuilder.get_object("treeview_track_list")
        self.__treeview_track.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        t = TrackListingModel
        if DEBUG_ID:
            col = gtk.TreeViewColumn("object ID", gtk.CellRendererText(), text=t.OBJECT_ID)
            self.__treeview_track.append_column(col)
            col = gtk.TreeViewColumn("parent ID", gtk.CellRendererText(), text=t.PARENT_ID)
            self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("title", gtk.CellRendererText(), text=t.TITLE)
        col.set_sort_column_id(t.TITLE)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("artist", gtk.CellRendererText(), text=t.ARTIST)
        col.set_sort_column_id(t.ARTIST)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("album", gtk.CellRendererText(), text=t.ALBUM)
        col.set_sort_column_id(t.ALBUM)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("genre", gtk.CellRendererText(), text=t.GENRE)
        col.set_sort_column_id(t.GENRE)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("length", gtk.CellRendererText(), text=t.LENGTH_STR)
        col.set_sort_column_id(t.LENGTH_INT)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("date", gtk.CellRendererText(), text=t.DATE)
        col.set_sort_column_id(t.DATE)
        self.__treeview_track.append_column(col)

        # add drag and drop support
        # @TODO: deactivate if not connected
        self.__treeview_track.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY)
        self.__treeview_track.connect('drag_data_received', self.on_drag_data_received)

        # create the file view
        self.__treeview_file = self.gtkbuilder.get_object("treeview_file_list")
        self.__treeview_file.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        f = FileTreeModel
        if DEBUG_ID:
            col = gtk.TreeViewColumn("object ID", gtk.CellRendererText(), text=f.OBJECT_ID)
            self.__treeview_file.append_column(col)
            col = gtk.TreeViewColumn("parent ID", gtk.CellRendererText(), text=f.PARENT_ID)
            self.__treeview_file.append_column(col)
        col = gtk.TreeViewColumn("filename", gtk.CellRendererPixbuf(), icon_name=f.ICON)
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=f.FILENAME)    
        col.set_sort_column_id(f.FILENAME)
        self.__treeview_file.append_column(col)
        col = gtk.TreeViewColumn("length", gtk.CellRendererText(), text=f.LENGTH_STR)
        col.set_sort_column_id(f.LENGTH_INT)
        self.__treeview_file.append_column(col)
        self.__treeview_file.expand_all() 
        # add drag and drop support
        # @TODO: deactivate if not connected
        self.__treeview_file.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY)
        self.__treeview_file.connect('drag_motion', self.on_drag_motion)
        self.__treeview_file.connect('drag_drop', self.on_drag_drop)
        self.__treeview_file.connect('drag_data_received', self.on_drag_data_received)

        self.connect_or_disconnect_device()
        self.window.show()

    def __getWidget(self, widget_id):
        return self.gtkbuilder.get_object(widget_id)

    #------ EVENTS ----------------------------------
    def on_button_create_folder_clicked(self, emiter):
        dlg = GetTextDialog(self.window, "Enter the new folder name:")
        new_folder_name = dlg.get_text()
        if new_folder_name and new_folder_name<>"":
            # find the last selected row ? FIXME: what to do there if more rows are selected?
            selrow_metadata = None
            selected = self.__get_currently_selected_rows_metadata()
            if selected: 
                selrow_metadata = selected[-1]
            parent_id=0
            if selrow_metadata:
                parent_id = selrow_metadata.id
                debug_trace("create folder on item %s" % parent_id, sender=self)
                # if the row is not a folder, take the parent which should be one
                if selrow_metadata.type <> Metadata.TYPE_FOLDER:
                    parent_id  = selrow_metadata.parent_id
                    debug_trace("It was not a folder. Its parent %s is taken instead." % parent_id, sender=self)

            self.__transferManager.create_folder(new_folder_name, parent_id)
        
    def on_delete_files_activate(self, emiter):
        #store the files id to delete before stating deleted, else, path may change if more line are selecetd
        to_del = [] 
        folder_count = 0
        for row in self.__get_currently_selected_rows_metadata():
            to_del.append(row)
            if row.type == Metadata.TYPE_FOLDER:
                folder_count+=1
                
        if len(to_del)==0: return

        # show confirmation                
        msg = "You are about to delete %i files" % (len(to_del) - folder_count)
        if folder_count > 0:
            msg += " and %i folders\nAll the files contained within the folders will be destroyed as well" % folder_count
        confirm_dlg = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, msg)
        confirm_dlg.set_title("Confirm delete")
        response=confirm_dlg.run()
        confirm_dlg.destroy() 
        if response <> gtk.RESPONSE_OK:
            return

        # send order to transfer manager
        for metadata in to_del:
            if DEBUG: debug_trace("deleting file with ID %s (%s)" % (metadata.id, metadata.filename), sender=self)
            self.__transferManager.del_file(metadata)

    def on_button_cancel_job_clicked(self, emiter):
        (model, paths) = self.__transferManager.get_selection().get_selected_rows()
        to_cancel = [] #store the files id to delete before stating deleted, else, path may change if more line are selecetd
        for path in paths:
            job =  model.get_job(path)
            to_cancel.append(job)
        for job in to_cancel:
            self.__transferManager.cancel_job(job)

    def on_connect_activate(self, emiter):
        self.connect_or_disconnect_device()

    def on_quit_activate(self, emiter):
        self.exit()

    def on_window_mtpnav_destroy(self, widget):
        self.exit()

    def on_send_files_activate(self, widget):
        # find the last selected row ? FIXME: what to do there if more rows are selected?
        selrow_metadata = None
        selected = self.__get_currently_selected_rows_metadata()
        if selected:
            selrow_metadata = selected[-1]
            
        # create and open the file chooser
        title = "Select files to transfer to the device"
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        fs = gtk.FileChooserDialog(title, self.window, gtk.FILE_CHOOSER_ACTION_OPEN, buttons)
        fs.set_select_multiple(True)
        fs.set_default_response(gtk.RESPONSE_OK)
        #fs.set_current_folder("") #TODO: remember previous path
        response = fs.run()
        if response == gtk.RESPONSE_OK:
            for uri in fs.get_uris():
                self.send_file(uri, selrow_metadata)
        fs.destroy()
        
    def on_drag_motion(self, treeview, drag_context, x, y, time):
        self.window.present()    
        treeview.get_selection().set_mode( gtk.SELECTION_SINGLE)
        treeview.set_hover_selection(True)
        treeview.set_hover_expand(True)

    def on_drag_drop(self, treeview, drag_context, x, y, time, data):
        treeview.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        treeview.set_hover_selection(False)
        treeview.set_hover_expand(False)
        
    def on_drag_data_received(self, treeview, context, x, y, data, info, time):
        if data and data.format == 8:
            # find the row where data was dropped
            selrow_metadata = None
            drop_info = treeview.get_dest_row_at_pos(x, y)
            if drop_info:
                selrow_metadata = treeview.get_model().get_metadata(drop_info[0])
                
            # process the list containing dropped objects
            for uri in data.data.split('\r\n')[:-1]:
                self.send_file(uri, selrow_metadata)
        context.finish(True, False, time)
        #FIXME: reject if not a file? 

    def send_file(self, uri, selrow_metadata):
        """
            selected_row: the metadata of the selected row
        """
        assert not selrow_metadata or type(selrow_metadata) is type(Metadata.Metadata())

        parent_id=0
        if selrow_metadata:
            parent_id = selrow_metadata.id
            debug_trace("files where dropped on %s" % parent_id, sender=self)
            # if the row is not a folder, take the parent which should be one
            if selrow_metadata.type <> Metadata.TYPE_FOLDER:
                parent_id  = selrow_metadata.parent_id
                debug_trace("It was not a folder. Its parent %s is taken instead." % parent_id, sender=self)

        return self.__transferManager.send_file(uri, parent_id)
        
    def exit(self):
        self.window.destroy()
        gtk.main_quit()

    def __get_currently_selected_rows_metadata(self):
        tv = None
        selrow_metadata = None
        #get the current treeview
        if self.__treeview_file.is_focus():
            tv = self.__treeview_file
        elif self.__treeview_track.is_focus():
            tv = self.__treeview_track
        else:
             return None
        # find which (last) row was selected on which treeview
        selrow_metadata = []
        (model, paths) = tv.get_selection().get_selected_rows()
        if tv:
            for path in paths:
                selrow_metadata.append(model.get_metadata(path)) 
        return selrow_metadata
            
    def connect_or_disconnect_device(self):
        widgets = ["menuitem_send_files", "menuitem_delete_files", "button_add_file", "button_del_file", "hbox_device_information"]
        if self.__device_engine:
            self.__disconnect_device()
        else:
            self.__connect_device()

        sensible = (self.__device_engine is not None)
        for w in widgets:
            self.__getWidget(w).set_sensitive(sensible)

    def __connect_device(self):
        dev = MTPDevice()
        self.__device_engine = DeviceEngine(dev)
        if not self.__device_engine.connect_device():
            # TODO: notify connection failed
            self.__device_engine = None
            return
        tv = self.__getWidget("treeview_transfer_manager")
        notebook = self.__getWidget("notebook_device_info")
        self.__transferManager = TransferManager(self.__device_engine, tv, notebook)

        # update models
        model = self.__device_engine.get_track_listing_model()
        self.__treeview_track.set_model(model)
        model = self.__device_engine.get_file_tree_model()
        self.__treeview_file.set_model(model)

        # change menu and toobar label and stock
        #TODO: use gtk.Action and gtk.ActionGroup for menu and toolbutton
        # ou uimanager http://python.developpez.com/cours/pygtktutorial/php/pygtkfr/sec-UIManager.php
        text="Disconnect device"
        stock=gtk.STOCK_DISCONNECT
        #TODO self.__getWidget("button_connect").set_label(text)
        self.__getWidget("button_connect").set_stock_id(stock)
        #TODO self.__getWidget("menuitem_connect").set_label(text)
        img = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_LARGE_TOOLBAR)
        #TODO self.__getWidget("menuitem_connect").set_image(img)
        self.__getWidget("label_device_name").set_markup("<b>" + self.__device_engine.get_device().get_name() + "</b>")
        self.__getWidget("label_device_name2").set_markup("<b>" + self.__device_engine.get_device().get_name() + "</b>")

        # disk usage
        used = self.__device_engine.get_device().get_diskusage()[0]
        total = self.__device_engine.get_device().get_diskusage()[1]
        prog_bar = self.__getWidget("progressbar_disk_usage")
        prog_bar.set_fraction(float(used)/float(total))
        prog_bar.set_text("%s of %s" % (util.format_filesize(used), util.format_filesize(total)))

        # batterie level
        max = self.__device_engine.get_device().get_batterylevel()[0]
        current = self.__device_engine.get_device().get_batterylevel()[1]
        prog_bar = self.__getWidget("progressbar_batterie_level")
        fraction = float(current)/float(max)
        prog_bar.set_fraction(fraction)
        prog_bar.set_text("%i%%" % (fraction * 100))

        infos = self.__device_engine.get_device().get_information()
        text=""
        for info in infos:
            text += "<b>" + info[0] + ":</b> " + info[1] + "\n"
        self.__getWidget("label_information").set_markup(text)

    def __disconnect_device(self):
        self.__device_engine.disconnect_device()
        self.__device_engine = None
        self.__treeview_track.set_model(None)
        self.__treeview_file.set_model(None)

        # change menu and toobar label and stock
        text="Connect device"
        stock=gtk.STOCK_CONNECT
        self.__getWidget("button_connect").set_label(text)
        self.__getWidget("button_connect").set_stock_id(stock)
        self.__getWidget("menuitem_connect").set_label(text)
        img = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.__getWidget("menuitem_connect").set_image(img)
        self.__getWidget("label_device_name").set_markup("<b>No device connected</b>")
        self.__getWidget("label_device_name2").set_markup("<b>No device connected</b>")

        # device info
        prog_bar.set_fraction(0)
        prog_bar.set_text("")
        prog_bar.set_fraction(0)
        prog_bar.set_text("")
        self.__getWidget("label_information").set_text("No device connected")


class GetTextDialog(gtk.MessageDialog):
    def __init__(self, parent, message):
        gtk.MessageDialog.__init__(self, parent,  gtk.DIALOG_MODAL | 
            gtk.DIALOG_DESTROY_WITH_PARENT,  
            gtk.MESSAGE_QUESTION,  
            gtk.BUTTONS_OK_CANCEL,  
            None)  
        self.set_markup(message)  
        self.entry = gtk.Entry()  
        self.vbox.pack_end(self.entry, True, True, 0)  
        
    def get_text(self):  
        self.show_all()  
        text = None
        if self.run() == gtk.RESPONSE_OK:
            text = self.entry.get_text()  
        self.destroy()  
        return text  

if __name__ == "__main__":
    mtpnav = MTPnavigator()
    gtk.gdk.threads_init()
    gtk.main()


