"""
vending_machine
=====
Simulates a vending machine.

Configurable parameters::

    {
        "product_catalogue" : (optional) [ "name" : "Mars Bar", "price" : 0.80, "lifetime" : "P1000D", ... ]
    }

Device properties created::

    {
        <TODO>
    }

"""

# NOTE: Here we represent cash in CENTS (or whatever, not dollars) to avoid the many perils of floating-point
# Machines have "positions" which start at "10" top right. A "tray" in vending-machine parlance is a whole row of positions (but we don't use that concept here)

from device import Device
import random
import isodate
import logging

HOURS = 60*60
DAYS = HOURS*24

HEARTBEAT_INTERVAL = 1 * DAYS

max_stock_per_position = 10

max_vending_interval_S = 6 * HOURS
min_replenish_interval_S = 7 * DAYS
max_replenish_interval_S = 30 * DAYS

expiry_check_interval = 1 * HOURS

alert_check_interval =  1 * HOURS

cash_likelihood = 0.5   # How many transactions are done in cash?
cash_denominations = [1, 5, 10, 25, 50, 100, 500, 1000, 2000]

alerts = [
        { "alert" : "outage_alert",  "mtbf" : DAYS * 90,     "average_length" : HOURS * 3,   "allows_comms" : False,     "allows_vending" : False },
        { "alert" : "refrigeration_alert" , "mtbf" : DAYS * 180,"average_length" : DAYS * 3, "allows_comms" : True,      "allows_vending" : False },
        { "alert" : "tamper_alert",  "mtbf" : DAYS * 80,     "average_length" : DAYS * 1,    "allows_comms" : True,      "allows_vending" : False }
        ]

default_machine_types = [
    { "manufacturer" : "Wurlitzer", "rows" : 8, "columns" : 10 },
    { "manufacturer" : "Furlitzer", "rows" : 5, "columns" : 5 },
    { "manufacturer" : "Nurlitzer", "rows" : 7, "columns" : 7 }
]

default_product_catalogue = [
    { "name" : "Mars Bar (Mars)",                       "price" : 80,   "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Crunchie (Cadbury)",                    "price" : 60,   "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Double Decker (Cadbury)",               "price" : 56,   "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Snickers (Mars)",                       "price" : 80,   "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Kit Kat (Nestle)",                      "price" : 90,   "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Toblerone (Mondelez)",                  "price" : 130,  "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Galaxy (Mars)",                         "price" : 140,  "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Dairy Milk (Cadbury)",                  "price" : 130,  "category" : "candy", "lifetime" : 1000 * DAYS },
    { "name" : "Doritos (Frito Lay)",                   "price" : 130,  "category" : "snack", "lifetime" : 100 * DAYS },
    { "name" : "Evian (Danone)",                        "price" : 120,  "category" : "drink", "lifetime" : 1000 * DAYS },
    { "name" : "Spam Sandwich (Freshserve)",            "price" : 150,  "category" : "sandwich", "lifetime" : 3 * DAYS },
    { "name" : "Seafood selection (Freshserve)",        "price" : 300,  "category" : "sandwich", "lifetime" : 1 * DAYS },
    { "name" : "Crispy salad sandwich (Freshserve)",    "price" : 230,  "category" : "sandwich", "lifetime" : 1 * DAYS }
    ]


def position_name(r,c):
    return "position_"+chr(ord("1")+r)+chr(ord("0")+c)

def create_2d_array(rows, columns):
    return [[0 for c in range(columns)] for r in range(rows)]

class Vending_machine(Device):
    myRandom = random.Random()  # Use our own private random-number generator, so we will repeatably generate the same device ID's regardless of who else is asking for random numbers
    myRandom.seed(1234)
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.current_alert = None
        super(Vending_machine,self).__init__(instance_name, time, engine, update_callback, context, params)

        # Define machine
        machine_types = params["vending_machine"].get("machine_types", default_machine_types)
        t = Vending_machine.myRandom.randrange(len(machine_types))
        self.set_property("manufacturer", machine_types[t]["manufacturer"])
        self.machine_rows = machine_types[t]["rows"]
        self.machine_columns = machine_types[t]["columns"]

        # Create product catalogue
        if "product_catalogue" in params["vending_machine"]:
            self.product_catalogue = []
            for p in params["vending_machine"]["product_catalogue"]:
                e = {}
                e["name"] = p["name"]
                e["price"] = p["price"]
                e["category"] = p["category"]
                e["lifetime"] = isodate.parse_duration(p["lifetime"]).total_seconds()
                self.product_catalogue.append(e)
        else:
            self.product_catalogue = default_product_catalogue

        self.set_property("positions_total", self.machine_rows * self.machine_columns)

        # Put some stock in machine
        self.restock_time = create_2d_array(self.machine_rows, self.machine_columns)  # the time when each position was last restocked (to detect past-sellby date items). We don't send a literal restock_time property, we just "bonk" the *_event_restock and then we can look at use $ts/*_event_restock in DevicePilot
        self.stock_level = create_2d_array(self.machine_rows, self.machine_columns)
        self.product_number_in_position = create_2d_array(self.machine_rows, self.machine_columns)
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                product_number = Vending_machine.myRandom.randrange(len(self.product_catalogue))
                self.product_number_in_position[r][c] = product_number
                self.stock_level[r][c] = Vending_machine.myRandom.randrange(0, max_stock_per_position/2)   # Only ever half-stock to begin with
                self.restock_time[r][c] = self.engine.get_now()
        self.update_available_positions()

        self.set_property("heartbeat", True)    # Send a heartbeat immediately on boot

        # Put some cash in cashbox
        self.cashbox_initialise()

        self.tick_vending_machine_check_expiry(self)

        engine.register_event_in(Vending_machine.myRandom.random()*max_vending_interval_S, self.tick_vending_machine_vend, self, self)
        engine.register_event_in(min_replenish_interval_S + Vending_machine.myRandom.random()*(max_replenish_interval_S-min_replenish_interval_S), self.tick_vending_machine_replenish, self, self)
        engine.register_event_in(alert_check_interval, self.tick_alert_check, self, self)
        engine.register_event_in(HEARTBEAT_INTERVAL, self.tick_heartbeat, self, self)

    def comms_ok(self):
        return super(Vending_machine,self).comms_ok() and self.allowed_to_communicate()

    def external_event(self, event_name, arg):
        super(Vending_machine,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Vending_machine,self).close()

    # Private methods
    def get_level(self, r,c):
        return self.stock_level[r][c]

    def set_level(self, r,c, new_level):
        old_level = self.stock_level[r][c]
        self.stock_level[r][c] = new_level
        if ((old_level==0) and (new_level != 0)) or ((old_level != 0) and (new_level == 0)):    # The availability of this position has just changed
            self.update_available_positions()

    def catalogue_item(self, r,c):
        return self.product_catalogue[self.product_number_in_position[r][c]]

    def past_sellby_date(self, r,c):
        return self.engine.get_now() >= self.restock_time[r][c] + self.catalogue_item(r,c)["lifetime"]

    def price(self, r,c):
        return self.catalogue_item(r,c)["price"]

    def allowed_to_vend(self):
        if self.current_alert is None:
            return True
        return alerts[self.current_alert]["allows_vending"]

    def allowed_to_communicate(self):
        if self.current_alert is None:
            return True
        return alerts[self.current_alert]["allows_comms"]

    def tick_vending_machine_vend(self, _):
        r = Vending_machine.myRandom.randrange(0,self.machine_rows)
        c = Vending_machine.myRandom.randrange(0,self.machine_columns)
        level = self.get_level(r,c)
        if level < 1:
            self.set_property("event_log", "Attempt to vend from empty " + position_name(r,c), always_send=True)
        elif self.past_sellby_date(r,c):
            self.set_property("event_log", "Attempt to vend with goods past sell-by date from " + position_name(r,c), always_send=True)
        elif not self.allowed_to_vend():
            self.set_property("event_log", "Attempt to vend whilst in " + alerts[self.current_alert]["alert"] + " condition")
        else:
            self.set_level(r,c,level-1)
            self.set_property("vend_event_position", position_name(r,c))
            product = self.product_catalogue[self.product_number_in_position[r][c]]
            self.set_property("vend_event_product", product["name"])
            self.set_property("vend_event_category", product["category"])
            self.set_property("vend_event_price", self.price(r,c))
            self.accept_payment(self.catalogue_item(r,c)["price"])
        self.engine.register_event_in(Vending_machine.myRandom.random()*max_vending_interval_S, self.tick_vending_machine_vend, self, self)

    def tick_vending_machine_replenish(self, _):
        self.replenish()
        self.engine.register_event_in(min_replenish_interval_S + Vending_machine.myRandom.random()*(max_replenish_interval_S-min_replenish_interval_S), self.tick_vending_machine_replenish, self, self)

    def tick_vending_machine_check_expiry(self, _):
        self.check_expirys()
        self.engine.register_event_in(expiry_check_interval, self.tick_vending_machine_check_expiry, self, self)

    def tick_alert_check(self, _):
        if self.current_alert is not None:
            return

        for a in range(len(alerts)):
            chance = float(alert_check_interval) / alerts[a]["mtbf"]
            if Vending_machine.myRandom.random() < chance:
                self.current_alert = a
                self.set_property("alert", alerts[self.current_alert]["alert"])
                L = float(alerts[a]["average_length"])
                length = Vending_machine.myRandom.gauss(L, L/2)
                length = max(L/3, min(L*5, length))
                self.engine.register_event_in(length, self.tick_alert_cancel, self, self)
                break

        self.engine.register_event_in(alert_check_interval, self.tick_alert_check, self, self)

    def tick_alert_cancel(self, _):
        self.current_alert = None
        self.set_property("alert", None)

    def tick_heartbeat(self, _):
        self.set_property("heartbeat", True, always_send=True)
        self.engine.register_event_in(HEARTBEAT_INTERVAL, self.tick_heartbeat, self, self)

    def check_expirys(self):
        has_expired = False
        will_expire_in_6_hrs = False
        now = self.engine.get_now()
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                if self.stock_level[r][c] > 0: 
                    lifetime = self.product_catalogue[self.product_number_in_position[r][c]]["lifetime"]
                    restocked = self.restock_time[r][c]
                    if restocked + lifetime < now:
                        has_expired = True
                    if restocked + lifetime - 6*60*60 < now:
                        will_expire_in_6_hrs = True
        if self.get_property_or_None("expired") != has_expired:
            self.set_property("expired", has_expired)
        if self.get_property_or_None("expire_in_6_hrs") != will_expire_in_6_hrs:
            self.set_property("expire_in_6_hrs", will_expire_in_6_hrs)

    def update_available_positions(self):
        avail_count = 0
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                    if self.get_level(r,c) > 0:
                        avail_count += 1
        self.set_property("positions_available", avail_count)

    def replenish(self):
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                if self.past_sellby_date(r,c):
                    self.set_property("event_log", "Disposed of expired food in "+position_name(r,c), always_send=True)
                    self.set_level(r,c, 0)
                if Vending_machine.myRandom.random() > 0.5:    # 50% chance of restocking any individual position 
                    if self.get_level(r,c) < max_stock_per_position:
                        self.set_property("event_log", "Restocking "+position_name(r,c), always_send=True)
                        self.set_level(r,c, max_stock_per_position)
                        # self.set_property(position_name(r,c)+"_event_restock", True, always_send=True)
                        self.restock_time[r][c] = self.engine.get_now()
        self.update_available_positions()
        self.set_property("event_log", "Emptying/restocking cashbox", always_send=True)
        old_cash = self.cashbox_cash()
        self.cashbox_initialise()
        new_cash = self.cashbox_cash()
        self.set_property("cash_recovered", old_cash - new_cash, always_send=True)
        self.set_property("event_replenish", True, always_send=True)
        self.set_property("event_log", "Replenishment complete", always_send=True)
        self.check_expirys()

    def cashbox_initialise(self):
        # Put a sensible selection of coins into cashbox
        self.cashbox = { 1 : 10, 5 : 10, 10 : 10, 25 : 10, 50 : 10, 100 : 10, 500 : 10 }
        self.cashbox_update()

    def make_change(self, value):
        i = len(self.cashbox)-1
        change = {}
        for i in range(len(self.cashbox)-1, -1, -1):    # Walk down through all denominations in cashbox
            denom = sorted(self.cashbox.keys())[i]
            num = int((value-bag_value(change)) / denom)
            num = min(num, self.cashbox[denom])         # Can't give more than we have
            if num > 0:
                add_to_bag(change, denom, num)
                remove_from_bag(self.cashbox, denom, num)

        if bag_value(change) != value:
            self.set_property("event_log", "Failed to make correct change. Change was " + str(value) + " but returned only "+str(bag_value(change)))
        return change

    def cashbox_cash(self):
        return bag_value(self.cashbox)

    def cashbox_update(self):
        self.set_property("cashbox_cash", self.cashbox_cash())

    def accept_payment(self, price):
        # Work out what coins were provided to pay for the goods
        if Vending_machine.myRandom.random() >= cash_likelihood:  # Smartcard payment
            self.set_property("vend_event_cashless", price, always_send=True)
        else:
            for biggest in range(len(cash_denominations)):   # Find index of denomination that's big-enough to pay outright
                if cash_denominations[biggest] >= price:
                    break
            if Vending_machine.myRandom.random() > 0.5:       # they just pay with a single unit of currency
                payment = { cash_denominations[biggest] : 1 }
            else:                           # they make up the payment with coins
                payment = {}
                for i in range(biggest-1, -1, -1):
                    num = int((price-bag_value(payment)) / cash_denominations[i])
                    if Vending_machine.myRandom.random() > 0.25:  # A chance that we don't have any smaller change, so we overpay with this denom
                        num += 1    # 
                    add_to_bag(payment, cash_denominations[i], num)
                    if bag_value(payment) >= price:
                        break
            self.set_property("vend_coins_accepted_total", bag_value(payment))
            add_bags(self.cashbox, payment)
            if bag_value(payment) != price:
                change = self.make_change(bag_value(payment) - price)
                self.set_property("vend_change_issued", str(change))
            self.cashbox_update()

# A "bag" is a set of cash denominations, with the value being the number of that denomination in the bag
def add_to_bag(bag, element, count=1):
    if element not in bag:
        bag[element] = 0
    bag[element] += count

def remove_from_bag(bag, element, count=1):
    assert element in bag, "Attempt to remove denomination from bag which does not contain it"
    assert bag[element] >= count, "Attempt to remove more of a denomination than bag has in it"
    bag[element] -= count

def add_bags(dest, src):
    for s in src:
        add_to_bag(dest, s, src[s])

def bag_value(bag):
    value = 0
    for (k,v) in bag.iteritems():
        value += k * v
    return value

