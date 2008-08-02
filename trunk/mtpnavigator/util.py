def format_filesize(bytesize, digits=2):
    """
    Formats the given size in bytes to be human-readable,

    Returns a localized "(unknown)" string when the bytesize
    has a negative value.

    Author: Thomas Perl (from gPodder)
    """
    units = (
            ( 'KB', 2**10 ),
            ( 'MB', 2**20 ),
            ( 'GB', 2**30 ),
    )

    try:
        bytesize = float( bytesize)
    except:
        return ""

    if bytesize < 0:
        return ""

    ( used_unit, used_value ) = ( 'B', bytesize )

    for ( unit, value ) in units:
        if bytesize >= value:
            used_value = bytesize / float(value)
            used_unit = unit

    return ('%.'+str(digits)+'f %s') % (used_value, used_unit)