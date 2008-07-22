def debug_trace(text, sender=None):
    print "(%s) %s" % (text, sender)
    
def trace(text, sender=None):
    print "(%s) %s" % (text, sender)
    
def notify_error(text):
    print "ERROR %s" % (text, sender)
    
def notify_warning(text):
    print "WARNING %s" % (text, sender)
