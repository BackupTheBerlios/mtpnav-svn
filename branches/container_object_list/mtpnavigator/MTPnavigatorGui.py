#!/usr/bin/env python
import pygtk
pygtk.require("2.0")
import gtk
import gobject
from DeviceEngine import DeviceEngine
from TransferManager import TransferManager
from notifications import *
from DeviceEngine import ObjectListingModel
from DeviceEngine import ContainerTreeModel
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

#display modes
MODE_PLAYLIST_VIEW = 0
MODE_FOLDER_VIEW = 1
MODE_ALBUM_VIEW = 2

class MTPnavigator:
    #--- INITIALISATION ----------------------------------

    def __init__(self):
        self.__treeview_track = None
        self.__treeview_navigator = None
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

        self.__create_track_view()
        self.__create_treeview_navigator()
        self.__create_combo_change_mode()

        self.window.show()
        self.on_connect_device()

    def __getWidget(self, widget_id):
        return self.gtkbuilder.get_object(widget_id)

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
                                 ('Delete', gtk.STOCK_DELETE, '_Delete', None, 'Delete the selected objects from device', self.on_delete_item_activate)
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

    def __create_track_view(self):
        self.__treeview_track = self.__getWidget("treeview_object_list")
        self.__treeview_track.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        t = ObjectListingModel

        # first column is file icon
        col = gtk.TreeViewColumn("")
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, True)
        col.set_attributes(cell, icon_name=t.ICON)
        col.set_sort_column_id(t.ICON)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.__treeview_track.append_column(col)

        # other columns to create: (visible, title, model_col, sort_col, sizing, width, resizable)
        cols = [(DEBUG_ID, "object ID", t.OBJECT_ID, t.OBJECT_ID, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, False)
        ,(DEBUG_ID, "parent ID", t.PARENT_ID, t.PARENT_ID, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, False)
        ,(DEBUG_ID, "type", t.TYPE, t.TYPE, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, False)
        ,(True, "file", t.FILE_NAME, t.FILE_NAME, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "title", t.TITLE, t.TITLE, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "artist", t.ARTIST, t.ARTIST, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "album", t.ALBUM, t.ALBUM, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "genre", t.GENRE, t.GENRE, gtk.TREE_VIEW_COLUMN_FIXED, COL_DEFAULT_WIDTH, True)
        ,(True, "length", t.SIZE_STR, t.SIZE_INT, gtk.TREE_VIEW_COLUMN_AUTOSIZE, -1, True)
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

        # add support for del key
        self.__treeview_track.add_events(gtk.gdk.KEY_PRESS)
        self.__treeview_track.connect("key_press_event", self.on_keyboard_event)

        # add drag and drop support
        self.__treeview_track.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self.__treeview_track.connect('drag_data_received', self.on_drag_data_received)

    def __create_treeview_navigator(self):
        # create the file view
        self.__treeview_navigator = self.__getWidget("treeview_navigator_list")
        self.__treeview_navigator.get_selection().set_mode( gtk.SELECTION_SINGLE)
        f = ContainerTreeModel
        if DEBUG_ID:
            col = gtk.TreeViewColumn("object ID", gtk.CellRendererText(), text=f.OBJECT_ID)
            self.__treeview_navigator.append_column(col)
            col = gtk.TreeViewColumn("parent ID", gtk.CellRendererText(), text=f.PARENT_ID)
            self.__treeview_navigator.append_column(col)
        col = gtk.TreeViewColumn("name")
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.set_attributes(cell, icon_name=f.ICON)
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=f.NAME)
        col.set_sort_column_id(f.NAME)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.__treeview_navigator.append_column(col)
        self.__treeview_navigator.set_headers_visible(False)

        #connect selection change event
        self.__treeview_navigator.get_selection().connect('changed', self.on_navigator_selection_change)

        # add support for del key
        self.__treeview_navigator.add_events(gtk.gdk.KEY_PRESS)
        self.__treeview_navigator.connect("key_press_event", self.on_keyboard_event)

        # add drag and drop support
        self.__treeview_navigator.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self.__treeview_navigator.connect('drag_motion', self.on_drag_motion)
        self.__treeview_navigator.connect('drag_drop', self.on_drag_drop)
        self.__treeview_navigator.connect('drag_data_received', self.on_drag_data_received)

    def __create_combo_change_mode(self):
        liststore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT)
        liststore.append(["audio-x-generic", "Playlists", MODE_PLAYLIST_VIEW]) #TRANSLATE
        liststore.append(["folder", "Folders", MODE_FOLDER_VIEW]) #TRANSLATE
        combobox = self.__getWidget("combo_change_mode")
        combobox.set_model(liststore)
        cell = gtk.CellRendererPixbuf()
        combobox.pack_start(cell, False)
        combobox.set_attributes(cell, icon_name=0)
        cell = gtk.CellRendererText()
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 1)
        combobox.connect('changed', self.on_combo_change_mode_changed)

    #--- EVENTS ----------------------------------

    def on_connect_device(self, widget=None):
        self.connect_device()

    def on_disconnect_device(self, widget=None):
        self.disconnect_device()

    def on_keyboard_event(self, treeview, event):
        if gtk.gdk.keyval_name(event.keyval) == "Delete":
            self.delete_objects(treeview)

    def on_create_folder(self, emiter):
        #FIXME: assert file mode
        parent_id = __get_currently_selected_folder()
        dlg = GetTextDialog(self.window, "Enter the new folder name:")
        new_folder_name = dlg.get_text()
        if new_folder_name and new_folder_name<>"":
            self.__transferManager.create_folder(new_folder_name, parent_id)

    def on_delete_item_activate(self, emiter):
        treeview = None
        if __treeview_navigator.is_focus():
            if DEBUG: debug_trace("Delete action activated. __treeview_navigator has focus", sender=self)
        if __treeview_track.is_focus():
            if DEBUG: debug_trace("Delete action activated. __treeview_track has focus", sender=self)
        if not treeview:
            if DEBUG: debug_trace("Delete action activated. No treeview has focus", sender=self)
            return
        self.delete_objects(treeview)

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
        parent_id = self.__get_currently_selected_folder()

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
                self.send_file(uri, parent_id)
        fs.destroy()

    def on_navigator_selection_change(self, treeselection):
        (model, iter) = treeselection.get_selected()
        if not iter: return
        metadata = model.get_metadata_from_iter(iter)
        folder = metadata.id
        if DEBUG: debug_trace("folder %s selected" % folder, sender=self)
        self.__device_engine.get_object_listing_model().set_current_folder(folder)

    def on_combo_change_mode_changed(self, combo):
        iter = combo.get_active_iter()
        mode = combo.get_model().get(iter, 2)[0]
        self.activate_mode(mode)

    def on_drag_motion(self, treeview, drag_context, x, y, time):
        treeview.drag_highlight()
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

    #--- CONTROL METHODS -----------------------

    def __get_currently_selected_folder(self):
        (model, iter)=self.__treeview_navigator.get_selection().get_selected()
        metadata = model.get_metadata_from_iter(iter)
        if metadata.type == Metadata.TYPE_FOLDER:
            return metadata.id
        return 0

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

    def connect_device(self):
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
        self.activate_mode(MODE_PLAYLIST_VIEW)

    def disconnect_device(self):
        self.__device_engine.disconnect_device()
        self.__device_engine = None
        self.__treeview_track.set_model(None)
        self.__treeview_folder.set_model(None)
        self.__show_connected_state(False)

    def activate_mode(self, mode):
        if DEBUG: debug_trace("activating mode %i" % mode, sender=self)
        track_model = None
        if mode == MODE_PLAYLIST_VIEW:
            track_model = self.__device_engine.get_track_listing_model()
            navigator_model = self.__device_engine.get_playlist_tree_model()
        elif mode == MODE_ALBUM_VIEW:
            track_model = self.__device_engine.get_track_listing_model()
            navigator_model = self.__device_engine.get_album_tree_model()
        elif mode == MODE_FOLDER_VIEW:
            track_model = self.__device_engine.get_file_listing_model()
            navigator_model = self.__device_engine.get_folder_tree_model()
        else:
            if DEBUG: debug_trace("unknow mode mode %i" % mode, sender=self)
            assert True
        self.__treeview_track.set_model(track_model)
        self.__treeview_navigator.set_model(navigator_model)
        self.__treeview_navigator.get_selection().select_path(0)
        self.__treeview_track.columns_autosize() # FIXME
        self.__treeview_navigator.expand_all()

    def send_file(self, uri, selrow_metadata):
        """
            selected_row: the metadata of the selected row
        """
        assert not selrow_metadata or type(selrow_metadata) is type(Metadata.Metadata())

        parent_id=0
        if selrow_metadata:
            parent_id = selrow_metadata.id
            if DEBUG: debug_trace("files where dropped on %s" % parent_id, sender=self)
            # if the row is not a folder, take the parent which should be one
            if selrow_metadata.type <> Metadata.TYPE_FOLDER:
                parent_id  = selrow_metadata.parent_id
                if DEBUG: debug_trace("It was not a folder. Its parent %s is taken instead." % parent_id, sender=self)

        return self.__transferManager.send_file(uri, parent_id)

    def delete_objects(self, treeview):
        #store the files id to delete before starting deleted, else, path may change if more line are selecetd
        to_del = []
        (folder_count, file_count, playlist_count, track_count) = (0, 0, 0, 0)
        (model, paths) = treeview.get_selection().get_selected_rows()
        for path in paths:
            to_del.append(treeview.get_model.get_metadata(path))
            if row.type == Metadata.TYPE_FOLDER: folder_count+=1
            if row.type == Metadata.TYPE_PLAYLIST: playlist_count+=1
            if row.type == Metadata.TYPE_FILE: file_count+=1
            if row.type == Metadata.TYPE_TRACK: track_count+=1

        if len(to_del)==0: return

        # show confirmation
        msg = "You are about to delete " #TRANSLATE
        if track_count > 0:  msg += " %i tracks" % track_count
        if file_count > 0:  msg += " %i files" % file_count
        if folder_count > 0: msg += " %i folders" % folder_count
        if playlist_count > 0: msg += " %i playlists" % playlist_count
        if folder_count > 0 : msg += "\nAll the files contained within the folders will be destroyed as well"
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

    def exit(self):
        self.window.destroy()
        gtk.main_quit()

if __name__ == "__main__":
    mtpnav = MTPnavigator()
    gtk.gdk.threads_init()
    gtk.main()
