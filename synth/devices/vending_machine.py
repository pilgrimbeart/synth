"""
vending_machine
=====
Simulates a vending machine.

Configurable parameters::

    {
    }

Device properties created::

    {
        <TODO>
    }

"""

from device import Device
import random

HOURS = 60*60
DAYS = HOURS*24

machine_rows = 3
machine_columns = 3
max_stock_per_tray = 10

max_vending_interval_S = 6 * HOURS
min_replenish_interval_S = 1 * DAYS
max_replenish_interval_S = 7 * DAYS

product_catalogue = [
        { "name" : "Mars Bar (Mars)",                       "price" : 0.80,   "lifetime" : 1000 * DAYS },
        { "name" : "Crunchie (Cadbury)",                    "price" : 0.60,   "lifetime" : 1000 * DAYS },
        { "name" : "Evian (Danone)",                        "price" : 1.20,   "lifetime" : 1000 * DAYS },
        { "name" : "Double Decker (Cadbury)",               "price" : 0.56,   "lifetime" : 1000 * DAYS },
        { "name" : "Snickers (Mars)",                       "price" : 0.80,   "lifetime" : 1000 * DAYS },
        { "name" : "Kit Kat (Nestle)",                      "price" : 0.90,   "lifetime" : 1000 * DAYS },
        { "name" : "Toblerone (Mondelez)",                  "price" : 1.30,   "lifetime" : 1000 * DAYS },
        { "name" : "Galaxy (Mars)",                         "price" : 1.40,   "lifetime" : 1000 * DAYS },
        { "name" : "Dairy Milk (Cadbury)",                  "price" : 1.30,   "lifetime" : 1000 * DAYS },
        { "name" : "Doritos (Frito Lay)",                   "price" : 1.30,   "lifetime" : 1000 * DAYS },
        { "name" : "Spam Sandwich (Freshserve)",            "price" : 1.50,   "lifetime" : 3 * DAYS },
        { "name" : "Seafood selection (Freshserve)",        "price" : 3.00,   "lifetime" : 1 * DAYS },
        { "name" : "Crispy salad and chips (Freshserve)",   "price" : 2.30,   "lifetime" : 1 * DAYS }
        ]

def tray_name(r,c):
    return "tray_"+chr(ord("A")+r)+chr(ord("1")+c)

def cent_rounding(n):
    return( int(n*100)/100.0 )

class Vending_machine(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.restock_time = {}   # indexed by tray_name, this is the time when each tray was last restocked (to detect past-sellby date items). We don't send a literal restock_time property, we just "bonk" the *_event_restock and then we can look at use $ts/*_event_restock in DevicePilot
        super(Vending_machine,self).__init__(instance_name, time, engine, update_callback, context, params)
        engine.register_event_in(self.myRandom.random()*max_vending_interval_S, self.tick_vending_machine_vend, self, self)
        engine.register_event_in(min_replenish_interval_S + self.myRandom.random()*(max_replenish_interval_S-min_replenish_interval_S), self.tick_vending_machine_replenish, self, self)
        for r in range(machine_rows):
            for c in range(machine_columns):
                product_number = self.myRandom.randrange(len(product_catalogue))
                product = product_catalogue[product_number]
                self.set_property(tray_name(r,c)+"_product_number", product_number)
                self.set_property(tray_name(r,c)+"_product_name", product["name"])
                self.set_property(tray_name(r,c)+"_price", product["price"])
                self.set_property(tray_name(r,c)+"_lifetime", product["lifetime"])
                self.set_property(tray_name(r,c)+"_stock_level",self.myRandom.randrange(0,max_stock_per_tray/2))    # Only ever half-fill trays to start with, so we see some trays getting empty
                self.set_property(tray_name(r,c)+"_event_restock", True, always_send=True)
                self.restock_time[tray_name(r,c)] = self.engine.get_now()
                
        self.update_available_trays()
        self.set_property("cashbox_cash", cent_rounding(3+self.myRandom.random()*10))

    def comms_ok(self):
        return super(Vending_machine,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Vending_machine,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Vending_machine,self).close()

    # Private methods
    def get_level(self, r,c):
        return self.get_property(tray_name(r,c)+"_stock_level")

    def set_level(self, r,c, level):
        self.set_property(tray_name(r,c)+"_stock_level", level)

    def past_sellby_date(self, r,c):
        item = product_catalogue[self.get_property(tray_name(r,c)+"_product_number")]
        return self.engine.get_now() >= self.restock_time[tray_name(r,c)] + item["lifetime"]

    def tick_vending_machine_vend(self, _):
        r = self.myRandom.randrange(0,machine_rows)
        c = self.myRandom.randrange(0,machine_columns)
        level = self.get_level(r,c)
        if level < 1:
            self.set_property("event_log", "Attempt to vend from empty "+tray_name(r,c), always_send=True)
        elif self.past_sellby_date(r,c):
            self.set_property("event_log", "Attempt to vend with goods past sell-by date from "+tray_name(r,c), always_send=True)
        else:
            self.set_property("event_log", "Successful vend from "+tray_name(r,c), always_send=True)
            self.set_level(r,c,level-1)
            if level==1: # Just vended last item
                self.update_available_trays()
            self.set_property("cashbox_cash", cent_rounding(self.get_property("cashbox_cash")+product_catalogue[self.get_property(tray_name(r,c)+"_product_number")]["price"]))
        self.engine.register_event_in(self.myRandom.random()*max_vending_interval_S, self.tick_vending_machine_vend, self, self)

    def tick_vending_machine_replenish(self, _):
        self.replenish()
        self.engine.register_event_in(min_replenish_interval_S + self.myRandom.random()*(max_replenish_interval_S-min_replenish_interval_S), self.tick_vending_machine_replenish, self, self)

    def update_available_trays(self):
        avail_count = 0
        for r in range(machine_rows):
            for c in range(machine_columns):
                    if self.get_level(r,c) > 0:
                        avail_count += 1
        self.set_property("trays_available", avail_count)

    def replenish(self):
        for r in range(machine_rows):
            for c in range(machine_columns):
                if self.past_sellby_date(r,c):
                    self.set_property("event_log", "Disposed of expired food in "+tray_name(r,c), always_send=True)
                    self.set_level(r,c, 0)
                if self.myRandom.random() > 0.5:    # 50% chance of restocking any individual tray
                    if self.get_level(r,c) < max_stock_per_tray:
                        self.set_property("event_log", "Restocking "+tray_name(r,c), always_send=True)
                        self.set_level(r,c, max_stock_per_tray)
                        self.set_property(tray_name(r,c)+"_event_restock", True, always_send=True)
                        self.restock_time[tray_name(r,c)] = self.engine.get_now()
        self.update_available_trays()
        self.set_property("event_log", "Emptying cashbox", always_send=True)
        self.set_property("cashbox_cash",0)
        self.set_property("event_replenish", True, always_send=True)
        self.set_property("event_log", "Replenishment complete", always_send=True)
