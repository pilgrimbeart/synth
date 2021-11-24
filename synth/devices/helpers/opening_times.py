"""
opening_times
=====
Produce realistic patterns of occupancy
"""
import logging
import time
from functools import lru_cache

#               0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  <- HOURS OF DAY
t86 =          [0,  0,  0,  0,  0,  0,  0,  1,  9,  9,  7,  7,  5,  7,  6,  5,  6,  7,  8,  1,  0,  0,  0,  0] 
t95 =          [0,  0,  0,  0,  0,  0,  0,  0,  1,  9,  7,  7,  5,  7,  6,  5,  6,  7,  1,  0,  0,  0,  0,  0] 
clo =          [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0]
rushhour =     [0,  0,  0,  0,  0,  0,  2,  4,  9,  6,  4,  2,  2,  3,  2,  2,  4,  6,  9,  8,  2,  1,  0,  0]
daytime =      [0,  0,  0,  0,  0,  0,  0,  2,  3,  4,  5,  5,  5,  5,  5,  4,  5,  6,  5,  4,  3,  2,  1,  1]
domestic =     [0,  0,  0,  0,  0,  1,  3,  5,  8,  6,  3,  3,  5,  2,  3,  4,  5,  8,  9,  8,  7,  6,  3,  1]
domestic_we =  [0,  0,  0,  0,  0,  0,  1,  3,  7,  8,  5,  3,  4,  5,  4,  4,  5,  6,  8,  8,  7,  7,  4,  1]

#                           [Mon,Tue,Wed,Thu,Fri,Sat,Sun]
patterns = {
        "nine_to_five" :    [t95,t95,t95,t95,t95,clo,clo],
        "eight_to_six" :    [t86,t86,t86,t86,t86,clo,clo],
        "six_day" :         [t95,t95,t95,t95,t95,t95,clo],
        "seven_day":        [t95,t95,t95,t95,t95,t95,t95],
        "rushhour":         [rushhour, rushhour, rushhour, rushhour, rushhour, daytime, daytime],
        "domestic" :        [domestic, domestic, domestic, domestic, domestic, domestic_we, domestic_we]
}

def float_to_index(f):
    return int(f * len(patterns))
    
def pick_pattern(randomfloat):
    """randomfloat is between [0..1)"""
    return list(patterns.keys())[float_to_index(randomfloat)]

day_prefix = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
def specification(pattern_name):
    """Returns opening hours specification like https://schema.org/openingHours"""
    patt = patterns[pattern_name]
    str = ""
    for day in range(7):
        start = None
        end = None
        for hour in range(24):
            if start is None:
                if patt[day][hour] != 0:
                    start = hour
            elif end is None:
                if patt[day][hour] == 0:
                    end = hour-1
        if start is not None:
            if end is None:
                end = 24
            str += day_prefix[day] + " %02d:00-%02d:00;"  % (start,end)
    return str

@lru_cache(maxsize=None)
def average_occupancy():
    """For all patterns chosen at random"""
    n = 0
    c = 0
    for patt in patterns:
        for day in patterns[patt]:
            for chance in day:
                c += chance
                n += 1
    c /= 9
    c /= float(n)
    return c

def chance_of_occupied(epoch, pattern_name = "nine_to_five"):
    t = time.gmtime(epoch) # Should be localised using lat/lon if available
    weekday = t.tm_wday  # Monday is 0
    hour = t.tm_hour + t.tm_min/60.0
    return patterns[pattern_name][weekday][int(hour)] * (1.0/9.0)  # Renormalise to 0.0..1.0

if __name__ == "__main__":
    for r in range(10):
        f = r/10.0
        print(pick_pattern(f), specification(pick_pattern(f)))
