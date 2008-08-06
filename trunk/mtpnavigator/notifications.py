import traceback
import sys

DEBUG=False
DEBUG_LOCK=False
DEBUG_ID=False
if "-d" in sys.argv: DEBUG=True
if "--debug-lock" in sys.argv: DEBUG_LOCK=True
if "--debug-id" in sys.argv: DEBUG_ID=True

def debug_trace(text, sender=None, exception=None):
    print "%s: %s" % (sender.__class__.__name__, text)
    if exception:
        error = traceback.format_exc()
        if error.strip() != 'None':
            print error

def trace(text, sender=None):
    print "%s: %s" % (sender.__class__.__name__, text)

def notify_error(text, exception=None):
    print "ERROR %s" % (text)
    if exception:
        error = traceback.format_exc()
        if error.strip() != 'None':
            print error

def notify_warning(text, exception=None):
    print "WARNING: %s" % (text)
    if exception:
        error = traceback.format_exc()
        if error.strip() != 'None':
            print error
