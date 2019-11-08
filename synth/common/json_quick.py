"""JSONquick
Faster JSON dumps"""

import json
import logging

def dumps(props):
    try:
        s = "{"
        for k,v in sorted(props.iteritems()):
            typ = type(v)
            s += '"' + k + '": '
            if typ in [str, unicode]: 
                s += '"' + str(v) + '"' #   Gets a decodeerror on some Unicode strings for reasons I can't fathom
            elif typ == bool:
                s += ["false","true"][v]
            else:
                s += str(v)
            s += ", "
        s = s[:-2] + "}"
        return s
    except:
        return json.dumps(props, sort_keys = True) # Fall back to the slow way!
