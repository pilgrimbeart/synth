# Analyse a Synth event file ../synth_logs/*.evt, and calculate for each minute of simulation:
# 1) How many devices have been created so far
# 2) How many messages have been seen so far
# This is mainly for crafting tests for partitioning, which require a certain amount of messages to fill pointfiles, and a certain number of devices to force partition-splitting

import sys

def get_properties(vars, vals):
    props = {}
    for p in zip(vars, vals):
        # name = p[0][1:-1]   # Strip quotes off name
        name = p[0]
        val = p[1]
        if val[0] in "\"'":
            val = val[1:-1] # Strip any quotes off value
        props[name] = val 
    return props

def analyse(lines):
    def print_stats():
        print("%10d" % int(rel_secs), "%7d" % int(rel_secs/60), "%5d" % int(rel_secs/(60*60)),  "%9d" % len(ids), "%10d" % msg_count)

    print("     rel_s   rel_m rel_h       ids       msgs")
    ids = set()
    start_time = None
    msg_count = 0
    prev_ts = None
    for line in lines:
        if line.startswith("***"):   # Comment
            continue;
        line = line[20:].strip()    # Strip off leading datestamp (we'll use $ts) and newline
        line = line[:-1]    # Strip off final comma
        sp = line.split(",")
        vars = sp[0::2]
        vals = sp[1::2]

        properties = get_properties(vars, vals)

        ids.add(properties["$id"])

        secs = float(properties["$ts"])
        if start_time is None:
            start_time = secs
            rel_secs = 0
        else:
            rel_secs = secs - start_time

        msg_count += 1

        if prev_ts == None:
            print_stats()   # First time through
        else:
            if int(prev_ts / 60) < int(rel_secs/60):    # Print stats for every new minute
                print_stats()
        prev_ts = rel_secs

    print_stats()   # After last message

        

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage:",sys.argv[0]," <filename>  where file is a .evt file")
        exit()
    analyse(open("../synth_logs/" + sys.argv[1] + ".evt").readlines())
