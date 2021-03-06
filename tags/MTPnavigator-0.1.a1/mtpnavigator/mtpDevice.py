import time

pymtp_available = True
try:
    import pymtp
except:
    pymtp_available = False
import Metadata

def date_to_mtp(date):
    """
    this function format the given date and time to a string representation
    according to MTP specifications: YYYYMMDDThhmmss.s

    return
        the string representation od the given date
    """
    if not date: return ""
    try:
        d = time.gmtime()
        s = []
        s.append(time.strftime("%Y",d))
        s.append(time.strftime("%m",d))
        s.append(time.strftime("%d",d))
        s.append("-") # free separator
        s.append(time.strftime("%H",d))
        s.append(time.strftime("%M",d))
        s.append(time.strftime("%S",d))
        s.append(".0Z") # indicates that a gmt time is storded
        return ''.join(s)
    except Exception, exc:
        return None

def mtp_to_date(mtp_string_date):
    """
    this parse the mtp's string representation for date
    according to specifications (YYYYMMDDThhmmss.s) to
    a python time object

    """
    mtp = mtp_string_date
    if not mtp or mtp=="": return None
    try:
        d = time.strptime(mtp[:8] + mtp[9:15],"%Y%m%d%H%M%S")
        _date = calendar.timegm(d)
        if len(mtp)==20:
            # TIME ZONE SHIFTING: the string contains a hour/min shift relative to a time zone
            try:
                shift_direction=mtp[15]
                hour_shift = int(mtp[16:18])
                minute_shift = int(mtp[18:20])
                shift_in_sec = hour_shift * 3600 + minute_shift * 60
                if shift_direction == "+":
                    _date += shift_in_sec
                elif shift_direction == "-":
                    _date -= shift_in_sec
                else:
                    raise ValueError("Expected + or -")
            except Exception, exc:
                print('WARNING: ignoring invalid time zone information for %s (%s)', mtp, exc)
        return _date
    except Exception, exc:
        print('WARNING: the mtp date "%s" can not be parsed against mtp specification (%s)', mtp, exc)
        return None


class MTPDevice():

    def __init__(self):
        self.__model_name = None
        self.__MTPDevice = pymtp.MTP()

    def __callback(self, sent, total):
        percentage = round(float(sent)/float(total)*100)
        text = ('%i%%' % percentage)

    def get_name(self):
        """
        this function try to find a nice name for the device.
        First, it tries to find a friendly (user assigned) name
        (this name can be set by other application and is stored on the device).
        if no friendly name was assign, it tries to get the model name (given by the vendor).
        If no name is found at all, a generic one is returned.

        Once found, the name is cached internaly to prevent reading again the device

        return
            the name of the device
        """

        if self.__model_name:
             return self.__model_name

        self.__model_name = self.__MTPDevice.get_devicename() # actually libmtp.Get_Friendlyname
        if not self.__model_name or self.__model_name == "?????":
            self.__model_name = self.__MTPDevice.get_modelname()
        if not self.__model_name:
            self.__model_name = "MTP device"

        return self.__model_name

    def connect(self):
        try:
            self.__MTPDevice.connect()
            # build the initial tracks_list
        except Exception, exc:
            print('unable to find an MTP device (%s)', exc)
            return False

        return True

    def close(self):
        try:
            self.__MTPDevice.disconnect()
        except Exception, exc:
            log('unable to close %s (%s)', self.get_name(), exc, sender=self)
            return False
        return True

    def send_track(self, metadata=None, callback=None):
        new_id =self.__MTPDevice.send_track_from_file( metadata.path, metadata.filename, metadata.to_MTPTrack(), callback=callback)
        metadata.id = str(new_id)
        return metadata

    def remove_track(self, track_id):
        t = int(track_id)
        return str(self.__MTPDevice.delete_object(t))

    def get_tracklisting(self):
        listing = []
        try:
            listing = self.__MTPDevice.get_tracklisting(callback=self.__callback)
        except Exception, exc:
            pass
            #log('unable to get file listing %s (%s)', exc, sender=self)

        tracks = []
        for track in listing:
            m = Metadata.get_from_MTPTrack(track)
            tracks.append(m)
        return tracks

    def get_diskusage(self):
        return [self.__MTPDevice.get_usedspace(), self.__MTPDevice.get_totalspace()]

    def get_batterylevel(self):
        return self.__MTPDevice.get_batterylevel()

    def get_information(self):
        info = []
        info.append(["Owner name", self.__MTPDevice.get_devicename()])
        info.append(["Manufacturer", self.__MTPDevice.get_manufacturer()])
        info.append(["Model name", self.__MTPDevice.get_modelname()])
        info.append(["Serial number", self.__MTPDevice.get_serialnumber()])
        info.append(["Firmware version", self.__MTPDevice.get_deviceversion()])
        return info

    def episode_on_device(self, episode):
        return episode.title in [ t.title for t in self.tracks_list ]
