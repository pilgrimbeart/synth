"""JSONquick
Faster JSON dumps"""

def dumps(props):
    s = "{"
    for k,v in sorted(props.iteritems()):
        typ = type(v)
        s += '"' + k + '": '
        if typ in [str, unicode]:
            s += '"' + str(v) + '"'
        elif typ == bool:
            s += ["false","true"][v]
        else:
            s += str(v)
        s += ", "
    s = s[:-2] + "}"
    return s
