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

from device import Device
import random
import isodate
import logging

HOURS = 60*60
DAYS = HOURS*24

machine_rows = 3
machine_columns = 3
max_stock_per_tray = 10

max_vending_interval_S = 6 * HOURS
min_replenish_interval_S = 1 * DAYS
max_replenish_interval_S = 7 * DAYS

expiry_check_interval = 1 * HOURS

alert_check_interval =  1 * HOURS

cash_likelihood = 0.5   # How many transactions are done in cash?
cash_denominations = [1, 5, 10, 25, 50, 100, 500, 1000, 2000]

alerts = [
        { "alert" : "outage_alert",  "mtbf" : DAYS * 90,     "average_length" : HOURS * 3,   "allows_comms" : False,     "allows_vending" : False },
        { "alert" : "refrigeration_alert" , "mtbf" : DAYS * 180,"average_length" : DAYS * 3, "allows_comms" : True,      "allows_vending" : False },
        { "alert" : "tamper_alert",  "mtbf" : DAYS * 80,     "average_length" : DAYS * 1,    "allows_comms" : True,      "allows_vending" : False }
        ]

default_product_catalogue = [
    { "name" : "Mars Bar (Mars)",                       "price" : 80,   "lifetime" : 1000 * DAYS },
    { "name" : "Crunchie (Cadbury)",                    "price" : 60,   "lifetime" : 1000 * DAYS },
    { "name" : "Evian (Danone)",                        "price" : 120,   "lifetime" : 1000 * DAYS },
    { "name" : "Double Decker (Cadbury)",               "price" : 56,   "lifetime" : 1000 * DAYS },
    { "name" : "Snickers (Mars)",                       "price" : 80,   "lifetime" : 1000 * DAYS },
    { "name" : "Kit Kat (Nestle)",                      "price" : 90,   "lifetime" : 1000 * DAYS },
    { "name" : "Toblerone (Mondelez)",                  "price" : 130,   "lifetime" : 1000 * DAYS },
    { "name" : "Galaxy (Mars)",                         "price" : 140,   "lifetime" : 1000 * DAYS },
    { "name" : "Dairy Milk (Cadbury)",                  "price" : 130,   "lifetime" : 1000 * DAYS },
    { "name" : "Doritos (Frito Lay)",                   "price" : 130,   "lifetime" : 1000 * DAYS },
    { "name" : "Spam Sandwich (Freshserve)",            "price" : 150,   "lifetime" : 3 * DAYS },
    { "name" : "Seafood selection (Freshserve)",        "price" : 300,   "lifetime" : 1 * DAYS },
    { "name" : "Crispy salad and chips (Freshserve)",   "price" : 230,   "lifetime" : 1 * DAYS }
    ]


def tray_name(r,c):
    return "tray_"+chr(ord("A")+r)+chr(ord("1")+c)

def create_2d_array(rows, columns):
    return [[0 for c in range(columns)] for r in range(rows)]

class Vending_machine(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.current_alert = None
        super(Vending_machine,self).__init__(instance_name, time, engine, update_callback, context, params)

        if "product_catalogue" in params["vending_machine"]:
            self.product_catalogue = []
            for p in params["vending_machine"]["product_catalogue"]:
                e = {}
                e["name"] = p["name"]
                e["price"] = p["price"]
                e["lifetime"] = isodate.parse_duration(p["lifetime"]).total_seconds()
                self.product_catalogue.append(e)
        else:
            self.product_catalogue = default_product_catalogue

        # Put some stock in machine
        self.restock_time = create_2d_array(machine_rows, machine_columns)  # the time when each tray was last restocked (to detect past-sellby date items). We don't send a literal restock_time property, we just "bonk" the *_event_restock and then we can look at use $ts/*_event_restock in DevicePilot
        self.stock_level = create_2d_array(machine_rows, machine_columns)
        self.product_number_in_tray = create_2d_array(machine_rows, machine_columns)
        for r in range(machine_rows):
            for c in range(machine_columns):
                product_number = self.myRandom.randrange(len(self.product_catalogue))
                self.product_number_in_tray[r][c] = product_number
                self.stock_level[r][c] = self.myRandom.randrange(0, max_stock_per_tray/2)   # Only ever half-stock to begin with
                self.restock_time[r][c] = self.engine.get_now()
        self.update_available_trays()

        # Put some cash in cashbox
        self.cashbox_initialise()

        self.tick_vending_machine_check_expiry(self)

        engine.register_event_in(self.myRandom.random()*max_vending_interval_S, self.tick_vending_machine_vend, self, self)
        engine.register_event_in(min_replenish_interval_S + self.myRandom.random()*(max_replenish_interval_S-min_replenish_interval_S), self.tick_vending_machine_replenish, self, self)
        engine.register_event_in(alert_check_interval, self.tick_alert_check, self, self)

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
        if ((old_level==0) and (new_level != 0)) or ((old_level != 0) and (new_level == 0)):    # The availability of this tray has just changed
            self.update_available_trays()

    def catalogue_item(self, r,c):
        return self.product_catalogue[self.product_number_in_tray[r][c]]

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
        r = self.myRandom.randrange(0,machine_rows)
        c = self.myRandom.randrange(0,machine_columns)
        level = self.get_level(r,c)
        if level < 1:
            self.set_property("event_log", "Attempt to vend from empty " + tray_name(r,c), always_send=True)
        elif self.past_sellby_date(r,c):
            self.set_property("event_log", "Attempt to vend with goods past sell-by date from " + tray_name(r,c), always_send=True)
        elif not self.allowed_to_vend():
            self.set_property("event_log", "Attempt to vend whilst in " + alerts[self.current_alert]["alert"] + " condition")
        else:
            self.set_level(r,c,level-1)
            self.set_property("vend_event_tray", tray_name(r,c))
            self.set_property("vend_event_product", self.product_catalogue[self.product_number_in_tray[r][c]]["name"])
            self.set_property("vend_event_price", self.price(r,c))
            self.accept_payment(self.catalogue_item(r,c)["price"])
        self.engine.register_event_in(self.myRandom.random()*max_vending_interval_S, self.tick_vending_machine_vend, self, self)

    def tick_vending_machine_replenish(self, _):
        self.replenish()
        self.engine.register_event_in(min_replenish_interval_S + self.myRandom.random()*(max_replenish_interval_S-min_replenish_interval_S), self.tick_vending_machine_replenish, self, self)

    def tick_vending_machine_check_expiry(self, _):
        self.check_expirys()
        self.engine.register_event_in(expiry_check_interval, self.tick_vending_machine_check_expiry, self, self)

    def tick_alert_check(self, _):
        if self.current_alert is not None:
            return

        for a in range(len(alerts)):
            chance = float(alert_check_interval) / alerts[a]["mtbf"]
            if random.random() < chance:
                self.current_alert = a
                self.set_property("alert", alerts[self.current_alert]["alert"])
                L = float(alerts[a]["average_length"])
                length = random.gauss(L, L/2)
                length = max(L/3, min(L*5, length))
                self.engine.register_event_in(length, self.tick_alert_cancel, self, self)
                break

        self.engine.register_event_in(alert_check_interval, self.tick_alert_check, self, self)

    def tick_alert_cancel(self, _):
        self.current_alert = None
        self.set_property("alert", None)

    def check_expirys(self):
        has_expired = False
        will_expire_in_6_hrs = False
        now = self.engine.get_now()
        for r in range(machine_rows):
            for c in range(machine_columns):
                if self.stock_level[r][c] > 0: 
                    lifetime = self.product_catalogue[self.product_number_in_tray[r][c]]["lifetime"]
                    restocked = self.restock_time[r][c]
                    if restocked + lifetime < now:
                        has_expired = True
                    if restocked + lifetime - 6*60*60 < now:
                        will_expire_in_6_hrs = True
        if self.get_property_or_None("expired") != has_expired:
            self.set_property("expired", has_expired)
        if self.get_property_or_None("expire_in_6_hrs") != will_expire_in_6_hrs:
            self.set_property("expire_in_6_hrs", will_expire_in_6_hrs)

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
                        # self.set_property(tray_name(r,c)+"_event_restock", True, always_send=True)
                        self.restock_time[r][c] = self.engine.get_now()
        self.update_available_trays()
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
        logging.info("Trying to make change of "+str(value))
        i = len(self.cashbox)-1
        change = {}
        for i in range(len(self.cashbox)-1, -1, -1):    # Walk down through all denominations in cashbox
            denom = sorted(self.cashbox.keys())[i]
            logging.info("value="+str(value)+" bag_value(change)="+str(bag_value(change)))
            num = int((value-bag_value(change)) / denom)
            logging.info("denom="+str(denom)+" num="+str(num))
            num = min(num, self.cashbox[denom])         # Can't give more than we have
            if num > 0:
                add_to_bag(change, denom, num)
                remove_from_bag(self.cashbox, denom, num)

        logging.info("Change is "+str(change))
        if bag_value(change) != value:
            logging.info("Failed to make change")
            self.set_property("event_log", "Failed to make correct change. Change was " + str(value) + " but returned only "+str(bag_value(change)))
        return change

    def cashbox_cash(self):
        return bag_value(self.cashbox)

    def cashbox_update(self):
        self.set_property("cashbox_cash", self.cashbox_cash())

    def accept_payment(self, price):
        # Work out what coins were provided to pay for the goods
        logging.info("cashbox was "+str(self.cashbox))
        if random.random() >= cash_likelihood:  # Smartcard payment
            self.set_property("vend_event_cashless", price, always_send=True)
        else:
            for biggest in range(len(cash_denominations)):   # Find index of denomination that's big-enough to pay outright
                if cash_denominations[biggest] >= price:
                    break
            if random.random() > 0.5:       # they just pay with a single unit of currency
                payment = { cash_denominations[biggest] : 1 }
            else:                           # they make up the payment with coins
                payment = {}
                for i in range(biggest-1, -1, -1):
                    num = int((price-bag_value(payment)) / cash_denominations[i])
                    if random.random() > 0.25:  # A chance that we don't have any smaller change, so we overpay with this denom
                        num += 1    # 
                    add_to_bag(payment, cash_denominations[i], num)
                    if bag_value(payment) >= price:
                        break
            logging.info("price="+str(price)+" payment="+str(payment))
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

