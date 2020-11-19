"""JSONquick
Faster JSON dumps"""

import json
import logging

def dumps(props):
    # return json.dumps(props, sort_keys = True) # Fall back to the slow way!
    # logging.info("jsonquick::dumps("+str(props)+")")
    s = "{"
    for k,v in sorted(props.items()):
        typ = type(v)
        s += '"' + k + '": '
        if v==None:
            s += "null"
        else:
            if typ is str: 
                s += '"' + str(v) + '"' 
            elif typ == bool:
                s += ["false","true"][v]
            else:
                s += str(v)
        s += ", "
    s = s[:-2] + "}"
    return s
