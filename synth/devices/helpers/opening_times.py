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
rushhour =     [1,  0,  0,  0,  0,  0,  2,  4,  9,  6,  4,  2,  2,  3,  2,  2,  4,  6,  9,  8,  6,  5,  4,  2]
daytime =      [0,  0,  0,  0,  0,  0,  0,  2,  3,  4,  5,  5,  5,  5,  5,  4,  5,  6,  5,  4,  3,  2,  1,  1]
domestic =     [1,  0,  0,  0,  0,  1,  3,  5,  8,  6,  3,  3,  5,  2,  3,  4,  5,  8,  9,  8,  7,  6,  6,  3]
domestic_we =  [1,  0,  0,  0,  0,  0,  1,  3,  7,  8,  5,  3,  4,  5,  4,  4,  5,  6,  8,  8,  7,  7,  6,  3]

#                           [Mon,Tue,Wed,Thu,Fri,Sat,Sun]
patterns = {
        "nine_to_five" :    [t95,t95,t95,t95,t95,clo,clo],
        "eight_to_six" :    [t86,t86,t86,t86,t86,clo,clo],
        "six_day" :         [t95,t95,t95,t95,t95,t95,clo],
        "seven_day":        [t95,t95,t95,t95,t95,t95,t95],
        "rushhour":         [rushhour, rushhour, rushhour, rushhour, rushhour, daytime, daytime],
        "domestic" :        [domestic, domestic, domestic, domestic, domestic, domestic_we, domestic_we]
}

def chance_of_occupied(epoch, pattern_name = "nine_to_five"):
    t = time.gmtime(epoch) # Should be localised using lat/lon if available
    weekday = t.tm_wday  # Monday is 0
    hour = t.tm_hour + t.tm_min/60.0
    return patterns[pattern_name][weekday][int(hour)] * (1.0/9.0)  # Renormalise to 0.0..1.0
