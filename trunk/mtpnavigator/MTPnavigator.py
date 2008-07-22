import gtk
from DeviceEngine import DeviceEngine
from mtpDevice import MTPDevice

class MTPnavigator:
    def __init__(self):
        self.__treeview_track = None
        self.__device_engine = None

        # bind to glade
        self.gtkbuilder = gtk.Builder()
        self.gtkbuilder.add_from_file("./mtpnavigator/MTPnavigator.xml")
        self.gtkbuilder.connect_signals(self)

        # create the track view
        self.__treeview_track = self.gtkbuilder.get_object("treeview_track_list")
        col = gtk.TreeViewColumn("treeview", gtk.CellRendererText(), text=0)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("artist", gtk.CellRendererText(), text=1)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("length", gtk.CellRendererText(), text=2)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("date", gtk.CellRendererText(), text=3)
        self.__treeview_track.append_column(col)

        # add drag and drop support
        # @TODO: deactivate if not connected
        self.__treeview_track.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY)
        self.__treeview_track.connect('drag_data_received', self.on_drag_data_received)

        self.connect_or_disconnect_device()

    def __getWidget(self, widget_id):
        return self.gtkbuilder.get_object(widget_id)
        
    #------ EVENTS ----------------------------------
    def __on_delete_files_activate(self, emiter):
        print "DELETE"

    def __on_connect_activate(self, emiter):
        self.connect_or_disconnect_device()

    def __on_window_destroy(self, widget):
        self.self.getWidget("window_mtpnav").destroy()
        gtk.main_quit()
        
    def __on_send_files_activate(self, widget):
        #@TODO
        pass

    def __on_drag_data_received(self, w, context, x, y, data, info, time):
        if data and data.format == 8:
            for uri in data.data.split('\r\n')[:-1]:
                self.send_file(uri)
        context.finish(True, False, time)
        

    def connect_or_disconnect_device(self):
        widgets = ["menuitem_send_files", "menuitem_delete_files", "button_add_file", "button_del_file", "hbox_device_information"]
        if self.__device_engine:
            self.__disconnect_device()
        else:
            self.__connect_device()

        sensible = (self.__device_engine is not None)
        for w in widgets:
            self.getWidget(w).set_sensitive(sensible)

    def __connect_device(self):
        dev = MTPDevice()
        self.__device_engine = DeviceEngine(dev)
        if not self.__device_engine.connect_device():
            # TODO: notify connection failed
            self.__device_engine = None
            return

        # update model
        model = self.__device_engine.get_track_listing_model()
        self.__treeview_track.set_model(model)

        # change menu and toobar label and stock
        text="Disconnect device"
        stock=gtk.STOCK_DISCONNECT
        self.getWidget("button_connect").set_label(text)
        self.getWidget("button_connect").set_stock_id(stock)
        self.getWidget("menuitem_connect").set_label(text)
        img = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.getWidget("menuitem_connect").set_image(img)
        self.getWidget("label_device_name").set_text(self.__device_engine.get_device().getName())

        # disk usage
        used = self.__device_engine.get_device().get_diskusage()[0]
        total = self.__device_engine.get_device().get_diskusage()[1]
        prog_bar = self.getWidget("progressbar_disk_usage")
        prog_bar.set_fraction(float(used)/float(total))
        prog_bar.set_text("%i of %i" % (used, total))

        # batterie level
        max = self.__device_engine.get_device().get_batterylevel()[0]
        current = self.__device_engine.get_device().get_batterylevel()[1]
        prog_bar = self.getWidget("progressbar_batterie_level")
        fraction = float(current)/float(max)
        prog_bar.set_fraction(fraction)
        prog_bar.set_text("%i%%" % (fraction * 100))

        #
        infos = self.__device_engine.get_device().get_information()
        text=""
        for info in infos:
            text += "<b>" + info[0] + ":</b> " + info[1] + "</br>"
        self.getWidget("label_information").set_text(text)

    def __disconnect_device(self):
        self.__device_engine.disconnect_device()
        self.__device_engine = None
        self.__treeview_track.set_model(None)
        
        # change menu and toobar label and stock
        text="Connect device"
        stock=gtk.STOCK_CONNECT
        self.getWidget("button_connect").set_label(text)
        self.getWidget("button_connect").set_stock_id(stock)
        self.getWidget("menuitem_connect").set_label(text)
        img = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.getWidget("menuitem_connect").set_image(img)
        self.getWidget("label_device_name").set_text("No device connected")
        
        # device info
        prog_bar.set_fraction(0)
        prog_bar.set_text("")
        prog_bar.set_fraction(0)
        prog_bar.set_text("")
        self.getWidget("label_information").set_text("No device connected")

    def send_file(self, uri):
        #self.getWidget("dialog_transfer").run()
        #TODO copy whole directory
        self.__device_engine.send_file(uri)

if __name__ == "__main__":
    mtpnav = MTPnavigator()
    mtpnav.window.show()
    gtk.main()


