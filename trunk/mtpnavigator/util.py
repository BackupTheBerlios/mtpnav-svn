def format_filesize(bytesize, use_si_units=False, digits=2):
    """
    Formats the given size in bytes to be human-readable,

    Returns a localized "(unknown)" string when the bytesize
    has a negative value.

    Author: Thomas Perl (from gPodder)
    """
    si_units = (
            ( 'kB', 10**3 ),
            ( 'MB', 10**6 ),
            ( 'GB', 10**9 ),
    )

    binary_units = (
            ( 'KiB', 2**10 ),
            ( 'MiB', 2**20 ),
            ( 'GiB', 2**30 ),
    )

    try:
        bytesize = float( bytesize)
    except:
        return _('(unknown)')

    if bytesize < 0:
        return _('(unknown)')

    if use_si_units:
        units = si_units
    else:
        units = binary_units

    ( used_unit, used_value ) = ( 'B', bytesize )

    for ( unit, value ) in units:
        if bytesize >= value:
            used_value = bytesize / float(value)
            used_unit = unit

    return ('%.'+str(digits)+'f %s') % (used_value, used_unit)