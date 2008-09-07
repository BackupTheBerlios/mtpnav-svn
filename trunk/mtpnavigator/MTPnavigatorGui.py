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
except Exception, exc:
    if DEBUG: debug_trace("can't import pymtp", exception=exc)
    pymtp_available = False

VERSION="0.1.a3"

DATA_PATH = os.path.join("/usr", "share", "mtpnavigator")
if "--local" in sys.argv or "-l" in sys.argv: DATA_PATH = "./data"
XML_GUI_FILE = os.path.join(DATA_PATH, "MTPnavigator.xml")

COL_DEFAULT_WIDTH = 200
TEXT_COLOR_GRAY = gtk.gdk.color_parse('#aaaaaa')
TEXT_COLOR_DEFAULT = None

#display modes
MODE_PLAYLIST_VIEW = 0
MODE_FOLDER_VIEW = 1
MODE_ALBUM_VIEW = 2

#drag and drop
DND_EXTERN = 0
DND_INTERN = 1
DND_TARGET_EXTERN_FILE = ('text/uri-list', 0, DND_EXTERN)
DND_TARGET_INTERN = ('INTERN', gtk.TARGET_SAME_APP, DND_INTERN)

class MTPnavigator:
    #--- INITIALISATION ----------------------------------

    def __init__(self):
        self.__device_engine = None
        self.transfer_manager = None
        self.__current_mode = None
        self.__current_folder = None

        # bind to glade
        self.gtkbuilder = gtk.Builder()
        self.gtkbuilder.add_from_file(XML_GUI_FILE)
        self.gtkbuilder.connect_signals(self)
        self.window = self.__getWidget("window_mtpnav")
        uimanager = self.__create_uimanager()

        self.__treeview_files = TreeViewFiles(self)
        self.__treeview_navigator = TreeViewNavigator(self)
        self.__getWidget("scrolledwindow_navigator").add(self.__treeview_navigator)
        self.__treeview_navigator.set_property("visible",True)
        self.__getWidget("scrolledwindow_files").add(self.__treeview_files)
        self.__treeview_files.set_property("visible",True)

        TEXT_COLOR_DEFAULT = self.__getWidget("entry_add_object").get_style().text[gtk.STATE_NORMAL]

        wwidth=800  #TODO save size
        wheight=600
        self.window.set_default_size(wwidth, wheight)
        self.window.set_size_request(500,350)
        self.window.set_title("MTP navigatore " + VERSION)
        #self.__getWidget("vpaned_main").set_position(wheight-250) #TODO: save position

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
                    <menuitem action="SendFiles"/>
                    <menuitem action="Delete"/>
                    <menuitem action="CreateFolder"/>
                    <menuitem action="CreatePlaylist"/>
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
        self.__actiongroup_connected.add_actions([('SendFiles', gtk.STOCK_OPEN, '_Send files to device...', '<Control>S', 'Pickup files to transfer into the device', self.on_send_files),
                                 ('Delete', gtk.STOCK_DELETE, '_Delete', None, 'Delete the selected objects from device', self.on_delete_item_activate),
                                 ('CreateFolder', None, 'Create _folder', None, 'Add a new folder into the currently selected folder', self.on_create_folder_item_activate),
                                 ('CreatePlaylist', None, 'Create _playlist', None, 'Create a new palyist', self.on_create_playlist_item_activate)
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

    def on_delete_item_activate(self, emiter):
        treeview = None
        if self.__treeview_navigator.is_focus():
            if DEBUG: debug_trace("Delete action activated. __treeview_navigator has focus", sender=self)
            treeview = self.__treeview_navigator
        if self.__treeview_files.is_focus():
            if DEBUG: debug_trace("Delete action activated. __treeview_files has focus", sender=self)
            treeview = self.__treeview_files
        if not treeview:
            if DEBUG: debug_trace("Delete action activated. No treeview has focus", sender=self)
            return
        selection = treeview.get_selected_rows_metadata()
        self.delete_objects(selection)

    def on_create_folder_item_activate(self, emiter):
        dialog = GetTextDialog(self.window, "Enter the new folder name")
        if dialog.run() == gtk.RESPONSE_OK: #TRANSLATE
            self.__create_folder(dialog.get_text())
        dialog.destroy()

    def on_create_playlist_item_activate(self, emiter):
        dialog = GetTextDialog(self.window, "Enter the new playlist name")
        if dialog.run() == gtk.RESPONSE_OK: #TRANSLATE
            self.__create_playlist(dialog.get_text())
        dialog.destroy()

    def on_button_cancel_job_clicked(self, emiter):
        (model, paths) = self.transfer_manager.get_selection().get_selected_rows()
        to_cancel = [] #store the files id to delete before stating deleted, else, path may change if more line are selecetd
        for path in paths:
            job =  model.get_job(path)
            to_cancel.append(job)
        for job in to_cancel:
            self.transfer_manager.cancel_job(job)

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
                self.transfer_manager.send_file(uri, parent_id)
        fs.destroy()

    def on_combo_change_mode_changed(self, combo):
        iter = combo.get_active_iter()
        mode = combo.get_model().get(iter, 2)[0]
        self.activate_mode(mode)

    def on_btn_add_object_clicked(self, button):
        new_object = self.__getWidget("entry_add_object").get_text()
        self.__empty_new_object_entry()
        if new_object=="" or new_object==self.__add_object_empty_text:
            msg = "Please, enter a name for the new element" #TRANSLATE
            notify_information(msg, sender=self.window)
            return
        if self.__current_mode == MODE_FOLDER_VIEW:
            self.__create_folder(new_object)
        elif self.__current_mode == MODE_PLAYLIST_VIEW:
            self.__create_playlist(new_object)
        else:
            if DEBUG: debug_trace("Unknow mode %i" % self.__current_mode, sender = self)
            assert False

    def on_entry_add_object_focus_in_event(self, widget, event):
        #widget.modify_text(gtk.STATE_NORMAL, self.default_entry_text_color)
        if widget.get_text() == self.__add_object_empty_text:
            widget.modify_text(gtk.STATE_NORMAL, TEXT_COLOR_DEFAULT)
            widget.set_text('')

    def on_entry_add_object_focus_out_event(self, widget, event):
        if widget.get_text() == '':
            widget.set_text(self.__add_object_empty_text)
            widget.modify_text(gtk.STATE_NORMAL, TEXT_COLOR_GRAY)

    #--- CONTROL METHODS -----------------------

    def __get_currently_selected_folder(self):
        return self.__current_folder

    def get_selected_rows_metadata(self, treeview):
        metadata = []
        (model, paths) = treeview.get_selection().get_selected_rows()
        for path in paths:
            if type(model) is type(gtk.TreeModelFilter()):
                row = model.get_model().get_metadata(model.convert_path_to_child_path(path))
            else:
                row = model.get_metadata(path)
            metadata.append(row)
        return metadata

    def __create_folder(self, new_folder_name):
        parent_id = self.__get_currently_selected_folder()
        self.transfer_manager.create_folder(new_folder_name, parent_id)

    def __create_playlist(self, new_playlist_name):
        self.transfer_manager.create_playlist(new_playlist_name)

    def __show_connected_state(self, is_connected):
        self.__actiongroup_connected.set_sensitive(is_connected)
        self.__actiongroup.get_action("Connect").set_visible(not is_connected)
        self.__actiongroup.get_action("Disconnect").set_visible(is_connected)
        self.__getWidget("hbox_device_information").set_sensitive(is_connected)
        self.__getWidget("scrolledwindow_files").set_sensitive(is_connected)
        self.__getWidget("vbox1").set_sensitive(is_connected)

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

    def __empty_new_object_entry(self, ):
        if self.__current_mode == MODE_PLAYLIST_VIEW:
            empty_text = "New playlist name..." #TRANSLATE
        elif self.__current_mode == MODE_FOLDER_VIEW:
            empty_text = "new folder name..." #TRANSLATE
        else:
            if DEBUG: debug_trace("Unknow mode %i" % self.__current_mode, sender = self)
            assert False

        self.__add_object_empty_text = empty_text
        entry = self.__getWidget("entry_add_object")
        entry.set_text(empty_text)
        entry.modify_text(gtk.STATE_NORMAL, TEXT_COLOR_GRAY)
        button = self.__getWidget("btn_add_object")

    def connect_device(self):
        self.__device_engine = None

        if "--dummy-device" in sys.argv:
            import dummyDevice
            dev = dummyDevice.DummyDevice()
        else:
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
        self.transfer_manager = TransferManager(self.__device_engine, tv, notebook,prog_bar)
        self.activate_mode(MODE_FOLDER_VIEW)
        self.__getWidget("combo_change_mode").set_active(MODE_PLAYLIST_VIEW)

    def disconnect_device(self):
        self.__device_engine.disconnect_device()
        self.__device_engine = None
        self.__treeview_files.set_model(None)
        self.__treeview_navigator.set_model(None)
        self.__show_connected_state(False)

    def activate_mode(self, mode):
        if DEBUG: debug_trace("activating mode %i" % mode, sender=self)
        track_model = None

        # show or hide cloumns
        t = self.__treeview_files
        file_columns_visible = [t.COL_FILE_NAME]
        track_columns_visible = [t.COL_TITLE, t.COL_ARTIST, t.COL_ALBUM, t.COL_GENRE]
        for col in file_columns_visible:
            t.get_column(col).set_visible(mode == MODE_FOLDER_VIEW)
        for col in track_columns_visible:
            t.get_column(col).set_visible(mode == MODE_PLAYLIST_VIEW)

        # set models
        if mode == MODE_PLAYLIST_VIEW:
            track_model = self.__device_engine.get_track_listing_model()
            navigator_model = self.__device_engine.get_playlist_tree_model()
        elif mode == MODE_FOLDER_VIEW:
            track_model = self.__device_engine.get_file_listing_model()
            navigator_model = self.__device_engine.get_folder_tree_model()
        else:
            if DEBUG: debug_trace("unknow mode %i" % mode, sender=self)
            assert False
        self.__treeview_files.set_model(track_model)
        self.__treeview_navigator.set_mode(mode)
        self.__treeview_navigator.set_model(navigator_model)
        self.__treeview_navigator.get_selection().select_path(0)
        self.__treeview_navigator.expand_all()
        self.__current_mode = mode
        self.__empty_new_object_entry()

    def change_current_folder(self, folder):
        self.__current_folder = folder
        self.__device_engine.get_object_listing_model().set_current_folder(folder)

    def delete_objects(self, to_del):
        if len(to_del)==0: return
        to_remove_from_playlist = []
        (folder_count, playlist_count, file_count, track_count) = (0, 0, 0, 0)

        for metadata in to_del:
            if metadata.type == Metadata.TYPE_FOLDER: folder_count+=1
            if metadata.type == Metadata.TYPE_PLAYLIST: playlist_count+=1
            if metadata.type == Metadata.TYPE_FILE: file_count+=1
            if metadata.type == Metadata.TYPE_TRACK: track_count+=1
            if metadata.type == Metadata.TYPE_PLAYLIST_ITEM:
                to_remove_from_playlist.append(metadata)
                to_del.remove(metadata)

        if len(to_del)>0:
            # show confirmation and delete objects
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
                self.transfer_manager.del_file(metadata)

        # remove tracks from playlist
        for metadata in to_remove_from_playlist:
            self.transfer_manager.remove_track_from_playlist(metadata)

    def exit(self):
        self.window.destroy()
        gtk.main_quit()

class TreeViewNavigator(gtk.TreeView):
    def __init__(self, gui):
        gtk.TreeView.__init__(self)
        self.__gui = gui
        self.__mode = None

        self.get_selection().set_mode( gtk.SELECTION_SINGLE)
        f = ContainerTreeModel
        if DEBUG_ID:
            col = gtk.TreeViewColumn("object ID", gtk.CellRendererText(), text=f.OBJECT_ID)
            self.append_column(col)
            col = gtk.TreeViewColumn("parent ID", gtk.CellRendererText(), text=f.PARENT_ID)
            self.append_column(col)
        col = gtk.TreeViewColumn("name")
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.set_attributes(cell, icon_name=f.ICON)
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=f.NAME)
        col.set_sort_column_id(f.NAME)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.append_column(col)
        self.set_headers_visible(False)

        #connect selection change event
        self.get_selection().connect('changed', self.on_selection_change)

        # add support for del key
        self.add_events(gtk.gdk.KEY_PRESS)
        self.connect("key_press_event", self.on_keyboard_event)

        # drag and drop source
        self.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, [DND_TARGET_INTERN], gtk.gdk.ACTION_MOVE)
        self.connect('drag_data_get', self.on_drag_data_get)

        # drag and drop destination
        self.enable_model_drag_dest([DND_TARGET_INTERN, DND_TARGET_EXTERN_FILE], gtk.gdk.ACTION_COPY)
        self.connect('drag_data_received', self.on_drag_data_received)

    def set_mode(self, mode):
        self.__mode = mode

    def on_keyboard_event(self, treeview, event):
        if gtk.gdk.keyval_name(event.keyval) == "Delete":
            selected = self.get_selected_rows_metadata()
            self.__gui.delete_objects(selected)

    def on_selection_change(self, treeselection):
        (model, iter) = treeselection.get_selected()
        if not iter: return
        metadata = model.get_metadata_from_iter(iter)
        folder = metadata.id
        if DEBUG: debug_trace("folder %s selected" % folder, sender=self)
        self.__gui.change_current_folder(folder)

    def on_drag_data_get(self, treeview, drag_context, data, info, time):
        selected = self.get_selected_row_metadata()
        d = []
        for metadata in selected:
            d.append(metadata.encode_as_string())
        data_string = "&&".join(d)
        if DEBUG: debug_trace("on_drag_data_get: send data %s" % data_string, sender=self)
        data.set(data.target, 8, data_string) # 8 = type string

    def on_drag_data_received(self, treeview, drag_context, x, y, data, info, time):
        # find the row where data was dropped
        selrow_metadata = None
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            selrow_metadata = treeview.get_model().get_metadata(drop_info[0])
        parent = selrow_metadata.id
        if selrow_metadata.type != Metadata.TYPE_FOLDER and selrow_metadata.type != Metadata.TYPE_PLAYLIST:
            parent = selrow_metadata.parent_id

        if info == DND_EXTERN:
            if DEBUG: debug_trace("extern drag and drop detected with data %s" % data.data, sender=self)
            if data and data.format == 8: # 8 = type string
                # process the list containing dropped objects
                for uri in data.data.split('\r\n')[:-1]:
                    if self.__mode == MODE_PLAYLIST_VIEW:
                        self.__gui.transfer_manager.send_extern_file_to_playlist(parent, uri, selrow_metadata)
                    else:
                        self.__gui.transfer_manager.send_file(uri, parent)
                drag_context.drop_finish(success=True, time=time)
            else:
                drag_context.drop_finish(success=False, time=time)
            return

        if info == DND_INTERN:
            for m in data.data.split("&&"):
                metadata = Metadata.decode_from_string(m)
                if DEBUG: debug_trace("intern drag and drop detected with data %s" % metadata.to_string(), sender=self)
                if self.__mode == MODE_PLAYLIST_VIEW:
                    if metadata.type != Metadata.TYPE_TRACK and metadata.type != Metadata.TYPE_PLAYLIST_ITEM:
                        drag_context.drop_finish(success=False, time=time)
                        if DEBUG: debug_trace("An invalid object type was dropped: %i" % i, sender=self)
                        return
                    self.__gui.transfer_manager.add_track_to_playlist(parent, metadata, selrow_metadata)
                else:
                    pass #TODO: move file to dir
            drag_context.drop_finish(success=True, time=time)
            return

        else:
            drag_context.drop_finish(success=False, time=time)
            if DEBUG: debug_trace("on_drag_data_received(): Unknow info value passed: %i" % info, sender=self)
            assert False

    def get_selected_row_metadata(self):
        (model, iter) = self.get_selection().get_selected()
        metadata = model.get_metadata_from_iter(iter)
        return metadata

    def get_selected_rows_metadata(self):
        return [self.get_selected_row_metadata()]


class TreeViewFiles(gtk.TreeView):
    first_col=0
    if DEBUG_ID: first_col=3
    COL_FILE_NAME = first_col + 1
    COL_TITLE = first_col + 2
    COL_ARTIST = first_col + 3
    COL_ALBUM = first_col + 4
    COL_GENRE = first_col + 5

    def __init__(self, gui):
        gtk.TreeView.__init__(self)
        self.__gui = gui

        self.get_selection().set_mode( gtk.SELECTION_MULTIPLE)
        t = ObjectListingModel

        # first column is file icon
        col = gtk.TreeViewColumn("")
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, True)
        col.set_attributes(cell, icon_name=t.ICON)
        col.set_sort_column_id(t.ICON)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.append_column(col)

        # other columns to create: (visible, title, model_col, sort_col, sizing, width, resizable)
        cols = [(DEBUG_ID, "object ID", t.OBJECT_ID, t.OBJECT_ID, -1)
        ,(DEBUG_ID, "parent ID", t.PARENT_ID, t.PARENT_ID, -1)
        ,(DEBUG_ID, "type", t.TYPE, t.TYPE, -1)
        ,(True, "file", t.FILE_NAME, t.FILE_NAME, COL_DEFAULT_WIDTH)
        ,(True, "title", t.TITLE, t.TITLE, COL_DEFAULT_WIDTH)
        ,(True, "artist", t.ARTIST, t.ARTIST, COL_DEFAULT_WIDTH)
        ,(True, "album", t.ALBUM, t.ALBUM, COL_DEFAULT_WIDTH)
        ,(True, "genre", t.GENRE, t.GENRE, COL_DEFAULT_WIDTH)
        ,(True, "length", t.SIZE_STR, t.SIZE_INT, -1)
        ,(True, "date", t.DATE_STR, t.DATE, -1)]

        for c in cols:
            if not c[0]: continue
            col = gtk.TreeViewColumn(c[1])
            cell = gtk.CellRendererText()
            col.pack_start(cell, True)
            col.set_attributes(cell, text=c[2])
            col.set_sort_column_id(c[3])
            if c[4]>0:
                col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                cell.set_property('ellipsize', pango.ELLIPSIZE_END)
                col.set_fixed_width(c[4])
                col.set_resizable(True)
            else:
                col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
                col.set_resizable(False)
            self.append_column(col)

        # add support for del key
        self.add_events(gtk.gdk.KEY_PRESS)
        self.connect("key_press_event", self.on_keyboard_event)

       # drag and drop source
        self.drag_source_set(gtk.gdk.BUTTON1_MASK, [DND_TARGET_INTERN], gtk.gdk.ACTION_MOVE)
        self.connect('drag_data_get', self.on_drag_data_get)

        # drag and drop destination
        #FIXME: make TreeModelFilter DND dest capable
        self.drag_dest_set(gtk.gdk.BUTTON1_MASK, [DND_TARGET_EXTERN_FILE], gtk.gdk.ACTION_COPY)
        self.connect('drag_data_received', self.on_drag_data_received)

    def on_drag_data_get(self, treeview, drag_context, data, info, time):
        selected = self.get_selected_rows_metadata()
        d = []
        for metadata in selected:
            d.append(metadata.encode_as_string())
        data_string = "&&".join(d)
        if DEBUG: debug_trace("on_drag_data_get: send data %s" % data_string, sender=self)
        data.set(data.target, 8, data_string) # 8 = type string

    def on_drag_data_received(self, treeview, drag_context, x, y, data, info, time):
        if info == DND_EXTERN:
            if DEBUG: debug_trace("extern drag and drop detected with data %s" % data.data, sender=self)
            if data and data.format == 8: # 8 = type string
                # find the row where data was dropped
                selrow_metadata = None
                drop_info = treeview.get_dest_row_at_pos(x, y)
                if drop_info:
                    selrow_metadata = treeview.get_model().get_metadata(drop_info[0])

                # process the list containing dropped objects
                for uri in data.data.split('\r\n')[:-1]:
                    self.send_file(uri, selrow_metadata)
                drag_context.drop_finish(success=True, time=time)
            else:
                drag_context.drop_finish(success=False, time=time)
        elif info == DND_INTERN:
            for m in data.data.split("&&"):
                metadata = Metadata.decode_from_string(m)
                if DEBUG: debug_trace("intern drag and drop detected with data %s" % metadata.to_string(), sender=self)
            drag_context.drop_finish(success=True, time=time)
        else:
            drag_context.drop_finish(success=False, time=time)
            if DEBUG: debug_trace("on_drag_data_received(): Unknow info value passed: %i" % info, sender=self)
            assert False

    def on_keyboard_event(self, treeview, event):
        if gtk.gdk.keyval_name(event.keyval) == "Delete":
            selected = self.get_selected_rows_metadata()
            self.__gui.delete_objects(selected)

    def get_selected_rows_metadata(self):
        metadata = []
        (model, paths) = self.get_selection().get_selected_rows()
        for path in paths:
            row = model.get_model().get_metadata(model.convert_path_to_child_path(path))
            metadata.append(row)
        return metadata

if __name__ == "__main__":
    mtpnav = MTPnavigator()
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()