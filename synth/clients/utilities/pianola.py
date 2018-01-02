import logging
import json
from PIL import Image
import numpy
import random
import math
import sys
import re

IMAGE_X = 1024
IMAGE_Y = 25480
LOG_DIR = "../../../../synth_logs/"

happy_devices = [   # All, sorted by 7-day uptime, best first
    73,
    131,
    136,
    159,
    174,
    180,
    183,
    185,
    274,
    277,
    315,
    337,
    367,
    387,
    392,
    398,
    401,
    402,
    418,
    425,
    431,
    453,
    458,
    460,
    478,
    495,
    508,
    509,
    512,
    513,
    516,
    517,
    519,
    532,
    535,
    542,
    547,
    557,
    587,
    598,
    627,
    639,
    659,
    693,
    695,
    714,
    866,
    878,
    922,
    968,
    978,
    986,
    1003,
    1066,
    1161,
    1208,
    1231,
    1241,
    636,
    654,
    875,
    167,
    602,
    429,
    621,
    244,
    264,
    537,
    205,
    642,
    107,
    143,
    204,
    41,
    299,
    329,
    243,
    75,
    323,
    493,
    503,
    123,
    217,
    46,
    403,
    238,
    221,
    127,
    219,
    249,
    218,
    126,
    164,
    100,
    163,
    197,
    268,
    78,
    544,
    629,
    334,
    196,
    473,
    99,
    92,
    474,
    101,
    200,
    105,
    195,
    79,
    50,
    321,
    156,
    117,
    248,
    215,
    225,
    91,
    192,
    271,
    198,
    103,
    49,
    186,
    256,
    212,
    42,
    631,
    152,
    202,
    96,
    162,
    229,
    232,
    538,
    201,
    149,
    449,
    153,
    386,
    363,
    300,
    1207,
    154,
    486,
    293,
    477,
    230,
    962,
    927,
    399,
    690,
    280,
    320,
    265,
    245,
    84,
    1177,
    168,
    301,
    520,
    624,
    929,
    246,
    1023,
    322,
    266,
    932,
    296,
    207,
    272,
    1222,
    234,
    179,
    276,
    373,
    223,
    208,
    918,
    691,
    450,
    90,
    963,
    594,
    83,
    423,
    459,
    692,
    839,
    480,
    482,
    937,
    656,
    380,
    491,
    539,
    635,
    378,
    231,
    383,
    314,
    38,
    302,
    216,
    361,
    295,
    181,
    210,
    304,
    259,
    137,
    199,
    1237,
    1098,
    1232,
    1230,
    1162,
    1000,
    132,
    836,
    227,
    662,
    1082,
    344,
    233,
    228,
    305,
    134,
    110,
    1025,
    226,
    850,
    391,
    1005,
    830,
    94,
    464,
    1183,
    980,
    801,
    102,
    599,
    490,
    689,
    575,
    632,
    340,
    252,
    858,
    983,
    1169,
    235,
    326,
    877,
    65,
    424,
    485,
    540,
    282,
    213,
    428,
    190,
    388,
    655,
    838,
    260,
    420,
    634,
    146,
    147,
    191,
    209,
    258,
    275,
    291,
    312,
    368,
    397,
    483,
    510,
    529,
    680,
    780,
    1099,
    1223,
    1238 ]

##happy_devices = [
##    73,
##    131,
##    136,
##    159,
##    174,
##    180,
##    183,
##    185,
##    274,
##    277,
##    315,
##    337,
##    367,
##    387,
##    392,
##    398,
##    401,
##    402,
##    418,
##    425,
##    431,
##    453,
##    458,
##    460,
##    478,
##    495,
##    508,
##    509,
##    512,
##    513,
##    516,
##    517,
##    519,
##    532,
##    535,
##    542,
##    547,
##    557,
##    587,
##    598,
##    627,
##    639,
##    659,
##    693,
##    695,
##    714,
##    866,
##    878,
##    922,
##    968,
##    978,
##    986,
##    1003,
##    1066,
##    1161,
##    1208,
##    1231,
##    1241]

##happy_devices = [
##    65,
##    73,
##    131,
##    136,
##    159,
##    174,
##    180,
##    183,
##    185,
##    274,
##    277,
##    315,
##    326,
##    336,
##    337,
##    340,
##    344,
##    366,
##    367,
##    375,
##    376,
##    382,
##    387,
##    392,
##    393,
##    396,
##    398,
##    401,
##    402,
##    414,
##    418,
##    425,
##    431,
##    453,
##    458,
##    460,
##    478,
##    487,
##    495,
##    497,
##    508,
##    509,
##    512,
##    513,
##    515,
##    516,
##    517,
##    519,
##    532,
##    535,
##    542,
##    547,
##    557,
##    569,
##    576,
##    587,
##    598,
##    627,
##    634,
##    636,
##    639,
##    654,
##    659,
##    693,
##    695,
##    714,
##    729,
##    730,
##    735,
##    737,
##    742,
##    743,
##    744,
##    751,
##    752,
##    754,
##    755,
##    756,
##    760,
##    766,
##    767,
##    800,
##    853,
##    860,
##    866,
##    875,
##    877,
##    878,
##    894,
##    898,
##    906,
##    917,
##    922,
##    945,
##    955,
##    960,
##    968,
##    978,
##    986,
##    995,
##    1003,
##    1025,
##    1066,
##    1115,
##    1127,
##    1134,
##    1161,
##    1173,
##    1176,
##    1178,
##    1181,
##    1183,
##    1196,
##    1208,
##    1231,
##    1241,
##    335,
##    1188 ]

nhd = []
for h in happy_devices:
    nhd.append(str(h))
happy_devices = nhd

def sorted_nicely( l ): 
    """ Sort the given iterable in the way that humans expect.""" 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)

def random_colour(N):
    # Given a number N, create a predictable RGB colour from it
    colour = (((N+123)*7489) % 256,
              hash((N+47)*4507) % 256,
              hash((N+433)*3371) % 256)

    return colour

def process(data):
    devices = []
    for event in data:
        I = event["$id"]
        if not I in devices:
            devices.append(I)
    devices = sorted_nicely(devices)
    logging.info(str(len(devices))+" devices")
    print "Devices found:",devices

    # Sort into happy and unhappy
    print "Happy devices",happy_devices
    d2 = happy_devices[:]
    for d in devices:
        if d not in d2:
            d2.append(d)
    devices = d2
    print "Final list",devices
    
    properties = []
    for event in data:
        for p in event:
            if p not in properties:
                properties.append(p)
    properties.sort()
    logging.info(str(len(properties))+" properties")
    logging.info(str(properties))

    num_prop_updates = 0
    for event in data:
        num_prop_updates += len(event)
    logging.info(str(num_prop_updates)+" property updates")
        
    earliest = None
    latest = None
    times = set()
    for event in data:
        T = event["$ts"]
        if earliest is None or T<earliest:
            earliest = T
        if latest is None or T>latest:
            latest = T
        if T not in times:
            times.add(T)
    logging.info("Time runs from "+str(earliest)+" to "+str(latest)+ " (i.e. " + str(latest-earliest) + " s)")
    logging.info(str(len(times))+" unique timestamps")

##    events_per_device = [0] * len(devices)
##    for event in data:
##        I = event["$id"]
##        events_per_device[devices.index(I)] += 1
##    for d in range(len(devices)):
##        print devices[d], events_per_device[d]

    arr = numpy.zeros((IMAGE_Y, IMAGE_X, 3), dtype=numpy.uint8)
    dots = 0
    for event in data:
        T = float(event["$ts"])
        x = int(math.floor((T-earliest)*IMAGE_X/(latest-earliest+1+len(properties))))

        if event["$id"] not in devices:
            continue #  !!!
        device_number = devices.index(event["$id"])
        for property_name in event:
            dots += 1
            property_number = properties.index(property_name)
            # y = int(math.floor(float(property_number) * IMAGE_Y / (len(properties)+1)))
            # y += random.randrange(0,50)
            # y = min(y, IMAGE_Y-1)
            # colour = random_colour(device_number)
            y = int(math.floor(float(device_number) * IMAGE_Y/ (len(devices) + len(properties) + 1)))
            y += property_number
            colour = random_colour(hash(event[property_name]))
            # colour = (255,255,255)
            # xp = x+random.randint(0,8)
            # yp = y+random.randint(0,8)
            x = min(x, IMAGE_X-1)
            y = min(y, IMAGE_Y-1)
            arr[y][x] = colour
            # arr[y][x] = (max(arr[y,x,0], colour[0]),  max(arr[y,x,1], colour[1]), max(arr[y,x,2], colour[2]))

    logging.info("Filling right")
    for y in range(IMAGE_Y):
        last = (0,0,0)
        for x in range(IMAGE_X):
            if all(arr[y][x] == (0,0,0)):
                arr[y][x] = last
            last = arr[y][x]
    
    logging.info("Plotted "+str(dots)+" dots total")
    return arr

def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    filename = LOG_DIR+sys.argv[1]+"_history.json"
    logging.info("Opening "+filename)
    data = json.loads(open(filename, "rt").read())

    arr = process(data)

    img = Image.fromarray(arr, "RGB")
    img.save(LOG_DIR+sys.argv[1]+"_history.png")

if __name__ == "__main__":
    main()
