#!/usr/bin/env python
import pygtk
pygtk.require("2.0")
import gtk
from DeviceEngine import DeviceEngine
from TransferManager import TransferManager
from notifications import *
from DeviceEngine import TrackListingModel
from DeviceEngine import FileTreeModel
import util
import Metadata
import pango
import os

try:
    import pymtp
    from mtpDevice import MTPDevice
    pymtp_available = True
except:
    pymtp_available = False


VERSION="0.1.a3"

DATA_PATH = os.path.join("/usr", "share", "mtpnavigator")
if "--local" in sys.argv or "-l" in sys.argv: DATA_PATH = "./data"
XML_GUI_FILE = os.path.join(DATA_PATH, "MTPnavigator.xml")

COL_DEFAULT_WIDTH = 200


class MTPnavigator:
    def __init__(self):
        self.__treeview_track = None
        self.__treeview_file = None
        self.__device_engine = None
        self.__transferManager = None

        # bind to glade
        self.gtkbuilder = gtk.Builder()
        self.gtkbuilder.add_from_file(XML_GUI_FILE)
        self.gtkbuilder.connect_signals(self)
        self.window = self.__getWidget("window_mtpnav")
        uimanager = self.__create_uimanager()

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
        # columns to create: (visible, title, model_col, sort_col, sizing, width, resizable)
        cols = [(DEBUG_ID, "object ID", t.OBJECT_ID, t.OBJECT_ID, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, False)
        ,(DEBUG_ID, "parent ID", t.PARENT_ID, t.OBJECT_ID, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, False)
        ,(True, "title", t.TITLE, t.TITLE, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "artist", t.ARTIST, t.ARTIST, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "album", t.ALBUM, t.ALBUM, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "genre", t.GENRE, t.GENRE, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "length", t.LENGTH_STR, t.LENGTH_INT, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, True)
        ,(True, "date", t.DATE_STR, t.DATE, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, True)]

        for c in cols:
            if not c[0]: continue
            col = gtk.TreeViewColumn(c[1])
            cell = gtk.CellRendererText()
            cell.set_property('ellipsize', pango.ELLIPSIZE_END)
            col.pack_start(cell, True)
            col.set_attributes(cell, text=c[2])
            col.set_sort_column_id(c[3])
            col.set_sizing(c[4])
            if c[5]>0: col.set_fixed_width(c[5])
            col.set_resizable(c[6])
            self.__treeview_track.append_column(col)

        # add drag and drop support
        # @TODO: deactivate if not connected
        self.__treeview_track.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
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
        col = gtk.TreeViewColumn("filename")
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.set_attributes(cell, icon_name=f.ICON)
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=f.FILENAME)
        col.set_sort_column_id(f.FILENAME)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_fixed_width(400)
        col.set_resizable(True)
        self.__treeview_file.append_column(col)
        col = gtk.TreeViewColumn("length", gtk.CellRendererText(), text=f.LENGTH_STR)
        col.set_sort_column_id(f.LENGTH_INT)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.__treeview_file.append_column(col)
        self.__treeview_file.expand_all()
        # add drag and drop support
        # @TODO: deactivate if not connected
        self.__treeview_file.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self.__treeview_file.connect('drag_motion', self.on_drag_motion)
        self.__treeview_file.connect('drag_drop', self.on_drag_drop)
        self.__treeview_file.connect('drag_data_received', self.on_drag_data_received)

        self.window.show()
        self.on_connect_device()

    def __create_uimanager(self):
        ui = '''
            <menubar name="MenuBar">
                <menu action="File">
                    <menuitem action="Connect"/>
                    <menuitem action="Disconnect"/>
                    <separator/>
                    <menuitem action="Quit"/>
                </menu>
                <menu  action="Device">
                    <menuitem action="CreateFolder"/>
                    <menuitem action="SendFiles"/>
                    <menuitem action="Delete"/>
                </menu>
            </menubar>
            <toolbar action="Toolbar">
                <toolitem action="Connect"/>
                <toolitem action="Disconnect"/>
                <separator/>
                <toolitem action="SendFiles"/>
                <toolitem action="Delete"/>
            </toolbar>
        '''

        self.__actiongroup = gtk.ActionGroup('MainActions')
        #TRANSLATE: see http://www.moeraki.com/pygtktutorial/pygtk2reference/class-gtkactiongroup.html#method-gtkactiongroup--set-translation-domain
        self.__actiongroup.add_actions([('File', None, '_File'),
                                 ('Device', None, '_Device'),
                                 ('Connect', gtk.STOCK_CONNECT, '_Connect', None, 'Connect the device', self.on_connect_device),
                                 ('Disconnect', gtk.STOCK_DISCONNECT, '_Disconnect', None, 'Disconnect the device', self.on_disconnect_device),
                                 ('Quit', gtk.STOCK_QUIT, '_Quit', None, 'Quit the Program', self.on_quit),
                                 ])
        self.__actiongroup_connected = gtk.ActionGroup('ActionConnected')
        self.__actiongroup_connected.add_actions([('CreateFolder', None, '_Create folder...', None, 'Create a folder into the selected folder', self.on_create_folder),
                                 ('SendFiles', gtk.STOCK_OPEN, '_Send files to device...', '<Control>S', 'Pickup files to transfer into the device', self.on_send_files),
                                 ('Delete', gtk.STOCK_DELETE, '_Delete', 'Delete', 'Delete the selected objects from device', self.on_delete_files)
                                 ])
        self.__actiongroup_connected.get_action('SendFiles').set_property('short-label', '_Send...')
        self.__actiongroup_connected.set_sensitive(False)
        self.__actiongroup.get_action("Disconnect").set_visible(False)

        uimanager = gtk.UIManager()
        uimanager.insert_action_group(self.__actiongroup, 0)
        uimanager.insert_action_group(self.__actiongroup_connected, 0)
        uimanager.add_ui_from_string(ui)

        self.window.add_accel_group(uimanager.get_accel_group())
        self.__getWidget("vbox_Menu_And_ToolBar").pack_start(uimanager.get_widget('/MenuBar'), expand=False)
        self.__getWidget("vbox_Menu_And_ToolBar").pack_start(uimanager.get_widget('/Toolbar'), expand=False)

    def __getWidget(self, widget_id):
        return self.gtkbuilder.get_object(widget_id)

    #------ EVENTS ----------------------------------
    def on_create_folder(self, emiter):
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

        if parent_id==0:
            # not allow to create folder on root
            msg = "You can't add a folder to the root.\nSelect which folder to create a new one into"
            notify_error(msg, title="Add folder", exception=None, sender=self.window)
            return

        dlg = GetTextDialog(self.window, "Enter the new folder name:")
        new_folder_name = dlg.get_text()
        if new_folder_name and new_folder_name<>"":
            self.__transferManager.create_folder(new_folder_name, parent_id)

    def on_delete_files(self, emiter):
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

    def on_quit(self, emiter):
        self.exit()

    def on_window_mtpnav_destroy(self, widget):
        self.exit()

    def on_send_files(self, widget):
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
        return #FIXME
        treeview.get_selection().set_mode( gtk.SELECTION_SINGLE)
        treeview.set_hover_selection(True)
        treeview.set_hover_expand(True)

    def on_drag_drop(self, treeview, drag_context, x, y, time, data):
        return #FIXME
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

    def on_connect_device(self, widget=None):
        self.__device_engine = None
        if not pymtp_available:
            msg = "pymtp is not or incorrectly installed on your system.\nThis is needed to access you device.\nGoto http://nick125.com/projects/pymtp to grab it and get installation instruction "
            notify_error(msg, title="pymtp not available", sender=self.window)
            self.__show_connected_state(False)
            return

        dev = MTPDevice()
        self.__device_engine = DeviceEngine(dev)
        try:
            self.__device_engine.connect_device()
        except Exception, exc:
            msg = "No device was found.\nPlease verify it was correctly plugged"
            notify_error(msg, title="No device found", exception=exc, sender=self.window)
            self.__device_engine = None
            self.__show_connected_state(False)
            return

        self.__show_connected_state(True)

        # FIXME Do not pass gui elements. use observer/observable instead
        tv = self.__getWidget("treeview_transfer_manager")
        notebook = self.__getWidget("notebook_device_info")
        prog_bar = self.__getWidget("progressbar_disk_usage")
        self.__transferManager = TransferManager(self.__device_engine, tv, notebook,prog_bar)
        # update models
        model = self.__device_engine.get_track_listing_model()
        self.__treeview_track.set_model(model)
        model = self.__device_engine.get_file_tree_model()
        self.__treeview_file.set_model(model)

    def on_disconnect_device(self, widget=None):
        self.__device_engine.disconnect_device()
        self.__device_engine = None
        self.__treeview_track.set_model(None)
        self.__treeview_file.set_model(None)
        self.__show_connected_state(False)


    def __show_connected_state(self, is_connected):
        self.__actiongroup_connected.set_sensitive(is_connected)
        self.__actiongroup.get_action("Connect").set_visible(not is_connected)
        self.__actiongroup.get_action("Disconnect").set_visible(is_connected)
        self.__getWidget("hbox_device_information").set_sensitive(is_connected)

        if is_connected:
            connected_device = self.__device_engine.get_device().get_name()
        else:
            connected_device = "No device connected" #TRANSLATE
        self.__getWidget("label_device_name").set_markup("<b>" + connected_device + "</b>")
        self.__getWidget("label_device_name2").set_markup("<b>" + connected_device + "</b>")

        if not is_connected:
            prog_bar = self.__getWidget("progressbar_disk_usage")
            prog_bar.set_fraction(0)
            prog_bar.set_text("")
            prog_bar = self.__getWidget("progressbar_batterie_level")
            prog_bar.set_fraction(0)
            prog_bar.set_text("")
            self.__getWidget("label_information").set_text("No device connected")
        else:
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

            # general information
            infos = self.__device_engine.get_device().get_information()
            text=""
            for info in infos:
                text += "<b>" + info[0] + ":</b> " + info[1] + "\n"
            self.__getWidget("label_information").set_markup(text)

if __name__ == "__main__":
    mtpnav = MTPnavigator()
    gtk.gdk.threads_init()
    gtk.main()
