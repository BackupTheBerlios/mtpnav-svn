#!/usr/bin/env python

import pygtk
pygtk.require("2.0")
import gtk
from DeviceEngine import DeviceEngine
from mtpDevice import MTPDevice
from TransferManager import TransferManager
from notifications import *
from DeviceEngine import TrackListingModel
import util

class MTPnavigator:
    def __init__(self):
        self.__treeview_track = None
        self.__device_engine = None
        self.__transferManager = None

        # bind to glade
        self.gtkbuilder = gtk.Builder()
        self.gtkbuilder.add_from_file("./mtpnavigator/MTPnavigator.xml")
        self.gtkbuilder.connect_signals(self)
        self.window = self.__getWidget("window_mtpnav")

        # create the track view
        self.__treeview_track = self.gtkbuilder.get_object("treeview_track_list")
        self.__treeview_track.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        t = TrackListingModel
        if DEBUG:
            col = gtk.TreeViewColumn("object ID", gtk.CellRendererText(), text=t.OBJECT_ID)
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

        self.connect_or_disconnect_device()
        self.window.show()

    def __getWidget(self, widget_id):
        return self.gtkbuilder.get_object(widget_id)

    #------ EVENTS ----------------------------------
    def on_delete_files_activate(self, emiter):
        (model, paths) = self.__treeview_track.get_selection().get_selected_rows()
        to_del = [] #store the files id to delete before stating deleted, else, path may change if more line are selecetd
        for path in paths:
            id =  model.get(model.get_iter(path), 0)[0] #FIXME: is there a better way?
            desc =  model.get(model.get_iter(path), 1)[0]
            to_del.append((id, desc))

        for (id, desc) in to_del:
            if DEBUG: debug_trace("deleting file with ID %s (%s)" % (id, desc), sender=self)
            self.__transferManager.del_file(id, desc)

    def on_connect_activate(self, emiter):
        self.connect_or_disconnect_device()

    def on_quit_activate(self, emiter):
        self.exit()

    def on_window_mtpnav_destroy(self, widget):
        self.exit()

    def on_send_files_activate(self, widget):
        title = "Select files to transfer to the device"
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)

        fs = gtk.FileChooserDialog(title, self.window, gtk.FILE_CHOOSER_ACTION_OPEN, buttons)
        fs.set_select_multiple(True)
        fs.set_default_response(gtk.RESPONSE_OK)
        #fs.set_current_folder("") #TODO: remember previous path
        response = fs.run()
        if response == gtk.RESPONSE_OK:
            for uri in fs.get_uris():
                self.send_file(uri)
        fs.destroy()

    def on_drag_data_received(self, w, context, x, y, data, info, time):
        if data and data.format == 8:
            for uri in data.data.split('\r\n')[:-1]:
                self.send_file(uri)
        context.finish(True, False, time)

    def exit(self):
        self.window.destroy()
        gtk.main_quit()

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

        # update model
        model = self.__device_engine.get_track_listing_model()
        self.__treeview_track.set_model(model)

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

        #
        infos = self.__device_engine.get_device().get_information()
        text=""
        for info in infos:
            text += "<b>" + info[0] + ":</b> " + info[1] + "\n"
        self.__getWidget("label_information").set_markup(text)

    def __disconnect_device(self):
        self.__device_engine.disconnect_device()
        self.__device_engine = None
        self.__treeview_track.set_model(None)

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

    def send_file(self, uri):
        #TODO copy whole directory
        self.__transferManager.send_file(uri)

if __name__ == "__main__":
    mtpnav = MTPnavigator()
    gtk.gdk.threads_init()
    gtk.main()


