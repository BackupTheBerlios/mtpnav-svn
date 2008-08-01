import traceback

DEBUG=True

def debug_trace(text, sender=None, exception=None):
    print "%s: %s" % (sender.__class__.__name__, text)
    if exception:
        error = traceback.format_exc()
        if error.strip() != 'None':
            print error

def trace(text, sender=None):
    print "%s: %s" % (sender.__class__.__name__, text)

def notify_error(text):
    print "ERROR %s" % (text)

def notify_warning(text, exception=None):
    print "WARNING: %s" % (text)
    if exception:
        error = traceback.format_exc()
        if error.strip() != 'None':
            print error    
