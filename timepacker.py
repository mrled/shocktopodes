import json
import datetime

time_fmt_Z      = '%Y-%m-%dT%H:%M:%SZ'  # The format with Z at the end, signifying UTC
time_fmt_offset = '%Y-%m-%dT%H:%M:%S%z' # The format with +/-HHMM at the end, signifying offset.

def unpack(timestamp):
    """
    Unpack a string object that conforms to variances of iso8601 into a
    datetime.datetime object.
    This code isn't really perfect? Because iso8601 is a little overbroad. 
    """
    if type(timestamp) is not str:
        e = "ERROR: Passed an object to unpack_timestamp() "
        e+= "that was not a string."
        raise Exception(e)
    try:
        # try the format with a Z at the end signifying UTC:
        ret = datetime.datetime.strptime(timestamp, time_fmt_Z)
        # if that works, it'll be valid, but without a .tzinfo attribute, and 
        # therefore it will be what python calls a "naive" object - unaware of
        # the timezone. 
        # munge it to include an offset of 00:00, and then reparse with strptime
        # so now we have a .tzinfo attribute, perfect
        new_timestamp = timestamp[0:-1] + "+0000"
        ret = datetime.datetime.strptime(new_timestamp, time_fmt_offset)
        return ret
    except ValueError as ve:
        pass
    
    try:
        # try the format with an offset of the format +/-HHMM (which is easy to
        # do in python because of %z). this ends up timezonified also.
        ret = datetime.datetime.strptime(timestamp, time_fmt_offset)
        return ret
    except ValueError as ve:
        pass

    try:
        # now try the same thing with a colon: +/-HH:MM (which is still correct 
        # rfc3339, but I have to munge the timestamp so that %z will take it)
        new_zoneinfo = timestamp[-6:-3] + timestamp[-2:]
        new_timestamp = timestamp[0:-6] + new_zoneinfo
        ret = datetime.datetime.strptime(new_timestamp, time_fmt_offset)
        return ret
    except ValueError as ve:
        pass

    raise Exception("Could not understand timestamp format.")

def pack(dt):
    """
    Pack a datetime object dt into a timestamp formatted for use with zk
    """
    if type(dt) is not datetime.datetime and type(dt) is not datetime.date:
        e = "ERROR: Passed an object to pack_timestamp() that was not a "
        e+= "datetime.datetime or a datetime.date."
        raise Exception(e)
    return dt.strftime('%Y-%m-%dT%H:%M:%S%z')
