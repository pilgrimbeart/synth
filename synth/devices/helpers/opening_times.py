"""
opening_times
=====
Produce realistic patterns of occupancy
"""
import logging
import time

#               0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  <- HOURS OF DAY
t86 =          [0,  0,  0,  0,  0,  0,  0,  1,  9,  9,  7,  7,  5,  7,  6,  5,  6,  7,  8,  1,  0,  0,  0,  0] 
t95 =          [0,  0,  0,  0,  0,  0,  0,  0,  1,  9,  7,  7,  5,  7,  6,  5,  6,  7,  1,  0,  0,  0,  0,  0] 
clo =          [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0]

#               Mon,Tue,Wed,Thu,Fri,Sat,Sun]
patterns = {
        "nine_to_five" :    [t95,t95,t95,t95,t95,clo,clo],
        "eight_to_six" :    [t86,t86,t86,t86,t86,clo,clo],
        "six_day" :         [t95,t95,t95,t95,t95,t95,clo],
        "seven_day":        [t95,t95,t95,t95,t95,t95,t95]
}

def chance_of_occupied(epoch, pattern_name = "nine_to_five"):
    t = time.gmtime(epoch) # Should be localised using lat/lon if available
    weekday = t.tm_wday  # Monday is 0
    hour = t.tm_hour + t.tm_min/60.0
    return patterns[pattern_name][weekday][int(hour)] * (1.0/9.0)  # Renormalise to 0.0..1.0
