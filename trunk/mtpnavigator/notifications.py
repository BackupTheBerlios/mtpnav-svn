import traceback
import sys
import gtk

DEBUG=False
if "-d" in sys.argv or "--debug" in sys.argv: DEBUG=True
DEBUG_LOCK=False
if "--debug-lock" in sys.argv: DEBUG_LOCK=True 
DEBUG_ID=False
if "--debug-id" in sys.argv: DEBUG_ID=True

def debug_trace(text, sender=None, exception=None):
    print "%s: %s" % (sender.__class__.__name__, text)
    if exception:
        error = traceback.format_exc()
        if error.strip() != 'None':
            print error

def trace(text, sender=None):
    print "%s: %s" % (sender.__class__.__name__, text)

def notify_error(message, title="Error", exception=None, sender=None):
    """
        Use this when you want to notify the user a blocking error
        has happend (pymtp not installed, impossible to connect device...)
        It will display a message box and print the error message
        to the error canal
    """
    notify_warning(message, Exception)
    dlg = gtk.MessageDialog(sender, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, message)
    dlg.run()
    dlg.destroy()    

def notify_warning(message, exception=None):
    """
        Use this when you want to notify the user a non blocking error
        has happend (impossible to get mp3 tags)
        It will only print the error message to the error canal
    """
    print "WARNING: %s" % (message)
    if exception:
        error = traceback.format_exc()
        if error.strip() != 'None':
            print error
