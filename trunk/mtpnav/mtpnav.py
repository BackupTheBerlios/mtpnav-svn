import sys
import gtk
from DeviceEngine import DeviceEngine
from mtpDevice import MTPDevice

class Mtpnav:

    def on_window_destroy(self, widget, data=None):
        self.window.destroy()
        gtk.main_quit()

    def __init__(self):
        self.__treeview_track = None
        self.__device_engine = None
        self.window = None

        self.gtkbuilder = gtk.Builder()
        self.gtkbuilder.add_from_file("data/mtpnav.xml")
        self.window = self.getWidget("window_mtpnav")
        self.gtkbuilder.connect_signals(self)

        self.__treeview_track = self.gtkbuilder.get_object("treeview_track_list")

        #drag and drop support
        self.__treeview_track.drag_dest_set(gtk.DEST_DEFAULT_ALL, [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY)
        self.__treeview_track.connect('drag_data_received', self.on_drag_data_received)

        self.connect_or_disconnect_device()

    def getWidget(self, widget_id):
        return self.gtkbuilder.get_object(widget_id)

    def connect_or_disconnect_device(self):
        widgets = ["button_add_file", "button_del_file", "hbox_device_information"]
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

        model = self.__device_engine.get_track_listing_model()
        self.__treeview_track.set_model(model)

        col = gtk.TreeViewColumn("treeview", gtk.CellRendererText(), text=0)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("artist", gtk.CellRendererText(), text=1)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("length", gtk.CellRendererText(), text=2)
        self.__treeview_track.append_column(col)
        col = gtk.TreeViewColumn("date", gtk.CellRendererText(), text=3)
        self.__treeview_track.append_column(col)
        self.getWidget("button_connect").set_label("Connect device")

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
            print info
            text += "<b>" + info[0] + ":</b> " + info[1] + "</br>"
        self.getWidget("label_information").set_text(text)

    def __disconnect_device(self):
        self.__device_engine.disconnect_device()
        self.__device_engine = None
        self.getWidget("button_connect").set_label("Disconnect device")

    def on_button_connect_clicked(self, button):
        self.connect_or_disconnect_device()

    def on_drag_data_received(self, w, context, x, y, data, info, time):
        if data and data.format == 8:
            for uri in data.data.split('\r\n')[:-1]:
                self.add_file(uri)
        context.finish(True, False, time)

    def add_file(self, uri):
        self.getWidget("dialog_transfer").run()

        self.__device_engine.add_file(uri)

if __name__ == "__main__":
    mtpnav = Mtpnav()
    mtpnav.window.show()
    gtk.main()

