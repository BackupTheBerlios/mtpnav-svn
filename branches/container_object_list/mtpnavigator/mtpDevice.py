import time
from notifications import *

import pymtp
import Metadata
import DeviceEngine
import time
import calendar

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
        s.append("T") # separator
        s.append(time.strftime("%H",d))
        s.append(time.strftime("%M",d))
        s.append(time.strftime("%S",d))
        s.append(".0Z") # indicates that a gmt time is storded
        return ''.join(s)
    except Exception, exc:
        if DEBUG: debug_trace("Error while processing date", exception=exc)
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
                if DEBUG: debug_trace('WARNING: ignoring invalid time zone information for %s (%s)', mtp, exc)
        return _date
    except Exception, exc:
        if DEBUG: debug_trace("the mtp date %s can not be parsed against mtp specification" % mtp, exc)
        return None


class MTPDevice():

    def __init__(self):
        self.__model_name = None
        self.__MTPDevice = pymtp.MTP()

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
        except pymtp.NoDeviceConnected, exc:
            raise DeviceEngine.DeviceError("Can't connect device")

    def disconnect(self):
        try:
            self.__MTPDevice.disconnect()
        except pymtp.NoDeviceConnected, exc:
            raise DeviceEngine.DeviceError("Can't disconnect device")

    def send_track(self, metadata=None, callback=None):
        parent = int(metadata.parent_id)
        try:
            new_id =self.__MTPDevice.send_track_from_file( metadata.path, metadata.filename, metadata.to_MTPTrack(), parent, callback=callback)
            # read metadata again, because they can be changed by the device (i.e. parent_id or paraneter not handled)
            metadata = Metadata.get_from_MTPTrack(self.__MTPDevice.get_track_metadata(new_id))
        except IOError:
            raise IOError("Failed to process the file from the filesystem") #TRANSLATE
        except pymtp.CommandFailed:
            if not self.__check_free_space(metadata.filesize):
                raise DeviceEngine.DeviceFullError("Not enought free space on device") #TRANSLATE
            if self.__file_exist(metadata.filename):
                raise DeviceEngine.AlreadyOnDeviceError("Already exists on the device") #TRANSLATE
            else:
                raise DeviceEngine.UnknowError("The device returned an unknow error") #TRANSLATE
        except Exception, exc:
            raise exc
        return metadata

    def create_folder(self, metadata=None):
        parent = metadata.parent_id
        assert parent<>0
        try:
            new_id =self.__MTPDevice.create_folder( metadata.filename, int(parent))
            metadata.id = new_id
        except pymtp.CommandFailed:
            if not self.__check_free_space(metadata.filesize):
                raise DeviceEngine.DeviceFullError("Not enought free space on device") #TRANSLATE
            if self.__file_exist(metadata.filename):
                raise DeviceEngine.AlreadyOnDeviceError("Already exists on the device") #TRANSLATE
            else:
                raise DeviceEngine.UnknowError("The device returned an unknow error") #TRANSLATE
        except Exception, exc:
            raise exc
        return metadata

    def remove_object(self, object_id):
        o = int(object_id)
        try:
            return True #str(self.__MTPDevice.delete_object(o))
        except pymtp.CommandFailed:
            raise DeviceEngine.UnknowError("The device returned an unknow error") #TRANSLATE
        except Exception, exc:
            raise exc
        return None

    def get_tracklisting(self):
        listing = []
        try:
            listing = self.__MTPDevice.get_tracklisting()
            tracks = []
            for track in listing:
                m = Metadata.get_from_MTPTrack(track)
                tracks.append(m)
            return tracks
        except pymtp.CommandFailed:
            raise DeviceEngine.UnknowError("The device returned an unknow error") #TRANSLATE
        except Exception, exc:
            raise exc
        return None

    def get_folder_list(self):
        listing = []
        try:
            listing = self.__MTPDevice.get_folder_list().values()
            folders = []
            for folder in listing:
                m = Metadata.get_from_MTPFolder(folder)
                folders.append(m)
            return folders
        except pymtp.CommandFailed:
            raise DeviceEngine.UnknowError("The device returned an unknow error") #TRANSLATE
        except Exception, exc:
            raise exc
        return None

    def get_filelisting(self):
        listing = []
        try:
            listing = self.__MTPDevice.get_filelisting()
            files = []
            for file in listing:
                m = Metadata.get_from_MTPFile(file)
                files.append(m)
            return files
        except pymtp.CommandFailed:
            raise DeviceEngine.UnknowError("The device returned an unknow error") #TRANSLATE
        except Exception, exc:
            raise exc
        return None

    def get_diskusage(self):
        return [self.__MTPDevice.get_usedspace(), self.__MTPDevice.get_totalspace()]

    def get_usedspace(self):
        return self.__MTPDevice.get_usedspace()

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

    def __check_free_space(self, objectsize):
        return objectsize <= self.__MTPDevice.get_freespace()

    def __file_exist(self, filename):
        file_names = []
        for file in self.get_filelisting():
             file_names.append(file.title)
        return filename in file_names