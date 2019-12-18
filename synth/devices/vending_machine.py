"""
vending_machine
=====
Simulates a vending machine.

Configurable parameters::

    {
            "product_catalogue" : (optional) [ "name" : "Mars Bar", "price" : 0.80, "category" : "snack", "lifetime" : "P1000D", ... ]
            "send_available_positions" : (optional) False
    }

Device properties created::

    {
        <TODO>
    }

"""

# NOTE: Here we represent cash in CENTS (or whatever, not dollars) to avoid the many perils of floating-point
# Machines have "positions" (a "tray" in vending-machine parlance is a whole row of positions but we don't use that concept here)

from .device import Device
import random
import isodate
import logging

HOURS = 60*60
DAYS = HOURS*24

HEARTBEAT_INTERVAL = 1 * DAYS

MAX_STOCK_PER_POSITION = 10

MAX_VENDING_INTERVAL_S = 6 * HOURS
MIN_REPLENISH_INTERVAL_S = 1 * DAYS
MAX_REPLENISH_INTERVAL_S = 14 * DAYS

EXPIRY_CHECK_INTERVAL = 1 * HOURS

ALERT_CHECK_INTERVAL =  1 * HOURS

CASH_LIKELIHOOD = 0.5   # How many transactions are done in cash?
CASH_DENOMINATIONS = [1, 5, 10, 25, 50, 100, 500, 1000, 2000]

alert_types = {
        "alertDoorOpen" :       { "mtbf" : DAYS * 90,   "average_length" : HOURS * 3,   "allows_comms" : True,  "allows_vending" : False },
        "alertTamper" :         { "mtbf" : DAYS * 180,  "average_length" : DAYS * 3,    "allows_comms" : True,  "allows_vending" : False },
        "alertTemperature" :    { "mtbf" : DAYS * 80,   "average_length" : DAYS * 1,    "allows_comms" : True,  "allows_vending" : False },
        "alertPowerOutage" :    { "mtbf" : DAYS * 80,   "average_length" : DAYS * 1,    "allows_comms" : False, "allows_vending" : False },
        "alertPaymentDevice" :  { "mtbf" : DAYS * 80,   "average_length" : DAYS * 1,    "allows_comms" : True,  "allows_vending" : False },
        "alertDropSensor" :     { "mtbf" : DAYS * 80,   "average_length" : DAYS * 1,    "allows_comms" : True,  "allows_vending" : False },
        "alertMotor" :          { "mtbf" : DAYS * 80,   "average_length" : DAYS * 1,    "allows_comms" : True,  "allows_vending" : False }
        }

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


def create_2d_array(rows, columns):
    return [[0 for c in range(columns)] for r in range(rows)]

class Vending_machine(Device):
    myRandom = random.Random()  # Use our own private random-number generator, so we will repeatably generate the same device ID's regardless of who else is asking for random numbers
    myRandom.seed(1234)
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.current_alerts = {}
        super(Vending_machine,self).__init__(instance_name, time, engine, update_callback, context, params)

        # Define machine
        machine_types = params["vending_machine"].get("machine_types", default_machine_types)
        t = Vending_machine.myRandom.randrange(len(machine_types))
        # self.set_property("manufacturer", machine_types[t]["manufacturer"])
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
                if "lifetime" in p:
                    e["lifetime"] = isodate.parse_duration(p["lifetime"]).total_seconds()
                self.product_catalogue.append(e)
        else:
            self.product_catalogue = default_product_catalogue

        self.send_available_positions = params["vending_machine"].get("send_available_positions", False)
        if self.send_available_positions:
            self.set_property("positions_total", self.machine_rows * self.machine_columns)

        # Put some stock in machine
        self.restock_time = create_2d_array(self.machine_rows, self.machine_columns)  # the time when each position was last restocked (to detect past-sellby date items). We don't send a literal restock_time property, we just "bonk" the *_event_restock and then we can look at use $ts/*_event_restock in DevicePilot
        self.stock_level = create_2d_array(self.machine_rows, self.machine_columns)
        self.product_number_in_position = create_2d_array(self.machine_rows, self.machine_columns)  # Indexes into product_catalogue[]
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                product_number = Vending_machine.myRandom.randrange(len(self.product_catalogue))
                self.product_number_in_position[r][c] = product_number
                self.stock_level[r][c] = Vending_machine.myRandom.randrange(0, MAX_STOCK_PER_POSITION/2)   # Only ever half-stock to begin with
                self.restock_time[r][c] = self.engine.get_now()
                self.send_stock_level_message(r,c)
        self.update_available_positions()

        self.send_heartbeat_message()

        # Put some cash in cashbox
        self.cashbox_initialise()

        self.send_initialization_message()

        self.tick_vending_machine_check_expiry(self)

        engine.register_event_in(Vending_machine.myRandom.random()*MAX_VENDING_INTERVAL_S, self.tick_vending_machine_vend, self, self)
        engine.register_event_in(MIN_REPLENISH_INTERVAL_S + Vending_machine.myRandom.random()*(MAX_REPLENISH_INTERVAL_S-MIN_REPLENISH_INTERVAL_S), self.tick_vending_machine_replenish, self, self)
        engine.register_event_in(ALERT_CHECK_INTERVAL, self.tick_alert_check, self, self)
        engine.register_event_in(HEARTBEAT_INTERVAL, self.tick_heartbeat, self, self)

    def comms_ok(self):
        return super(Vending_machine,self).comms_ok() and self.allowed_to_communicate()

    def external_event(self, event_name, arg):
        super(Vending_machine,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Vending_machine,self).close()

    # Private methods
    def alert_states(self):
        result = {}
        for a in alert_types:
            result[a] = a in self.current_alerts    # Define the T/F alert state for all possible alerts
        return result

    def allowed_to_x(self, x):
        for a in self.current_alerts:
            if alert_types[a][x] == False:
                return False
        return True

    def allowed_to_vend(self):
        return self.allowed_to_x("allows_vending")
        
    def allowed_to_communicate(self):
        return self.allowed_to_x("allows_comms")
        
    def position_number(self, r,c):
        return 1 + r * self.machine_columns + c

    def position_name(self, r,c): # Allows us to use different naming conventions for the positions
        #   return "position_" + chr(ord("1")+r) + chr(ord("0")+c)   Top left is "10"
        return "position_" + str(self.position_number(r,c))

    def get_level(self, r,c):
        return self.stock_level[r][c]

    def set_level(self, r,c, new_level):
        old_level = self.stock_level[r][c]
        self.stock_level[r][c] = new_level
        if ((old_level==0) and (new_level != 0)) or ((old_level != 0) and (new_level == 0)):    # The availability of this position has just changed
            self.update_available_positions()
            self.send_stock_level_message(r,c)

    def send_initialization_message(self):
        props = {
                "eventType" : "initialization",
                "isEnabled" : True,
                "cashboxCash" : self.cashbox_cash()
                }
        props.update(self.alert_changes({}, update_all = True))
        self.set_properties(props)

    def send_replenish_message(self, cash_collected):
        props = {
                "eventType" : "replenishment",
                "cashCollected" : cash_collected,
                "cashboxCash" : self.cashbox_cash()
                }
        self.set_properties(props)

    def send_stock_level_message(self, r, c):
        product = self.product_catalogue[self.product_number_in_position[r][c]]
        props = {
                "eventType" : "stockLevel",
                "name" : product["name"],
                "category" : self.catalogue_item(r,c)["category"],
                "price" : self.price(r,c),
                "location" : self.position_number(r,c),
                "qtyAvailable" : self.stock_level[r][c]
                }
        self.set_properties(props)

    def send_vending_detail_message(self,r,c):
        product = self.product_catalogue[self.product_number_in_position[r][c]]
        props = {
                "eventType" : "vendingDetail",
                "name" : product["name"],
                "category" : product["category"],
                "price" : product["price"],
                "currency" : "USD",
                "location" : self.position_number(r,c),
                "qtySold" : 1,
                "qtyAvailable" : self.stock_level[r][c],
                "error" : None
                }
        self.set_properties(props)

    def send_vending_summary_message(self,r,c, payment_type):
        product = self.product_catalogue[self.product_number_in_position[r][c]]
        props = {
            "eventType" : "vendingSummary",
            "paymentType" : payment_type,
            "totalPrice" : product["price"],
            "currency" : "USD",
            "cashboxCash" : self.cashbox_cash(),
            "allProductsWereDispensed" : True,
            "error" : None,
            "totalVendedQty" : 1
        }
        self.set_properties(props)

    def send_heartbeat_message(self):
        self.set_properties({"heartBeat" : True})

    def catalogue_item(self, r,c):
        return self.product_catalogue[self.product_number_in_position[r][c]]

    def past_sellby_date(self, r,c):
        if "lifetime" not in self.catalogue_item(r,c):
            return False
        return self.engine.get_now() >= self.restock_time[r][c] + self.catalogue_item(r,c)["lifetime"]

    def price(self, r,c):
        return self.catalogue_item(r,c)["price"]

    def tick_vending_machine_vend(self, _):
        r = Vending_machine.myRandom.randrange(0,self.machine_rows)
        c = Vending_machine.myRandom.randrange(0,self.machine_columns)
        level = self.get_level(r,c)
        if level < 1:
            pass # self.set_property("event_log", "Attempt to vend from empty " + self.position_name(r,c), always_send=True)
        elif self.past_sellby_date(r,c):
            pass # self.set_property("event_log", "Attempt to vend with goods past sell-by date from " + self.position_name(r,c), always_send=True)
        elif not self.allowed_to_vend():
            pass # self.set_property("event_log", "Attempt to vend whilst in an alert condition which prevents vending")
        else:
            # self.start_property_group() # -->
            self.set_level(r,c,level-1)
            # self.set_property("vend_event_position", self.position_name(r,c))
            product = self.product_catalogue[self.product_number_in_position[r][c]]
            # self.set_property("vend_event_product", product["name"])
            # self.set_property("vend_event_category", product["category"])
            # self.set_property("vend_event_price", self.price(r,c))
            payment_type = self.accept_payment(self.catalogue_item(r,c)["price"])
            # self.end_property_group()   # <--
            self.send_vending_detail_message(r,c)
            self.send_vending_summary_message(r,c,payment_type)
        self.engine.register_event_in(Vending_machine.myRandom.random()*MAX_VENDING_INTERVAL_S, self.tick_vending_machine_vend, self, self)

    def tick_vending_machine_replenish(self, _):
        self.replenish()
        self.engine.register_event_in(MIN_REPLENISH_INTERVAL_S + Vending_machine.myRandom.random()*(MAX_REPLENISH_INTERVAL_S-MIN_REPLENISH_INTERVAL_S), self.tick_vending_machine_replenish, self, self)

    def tick_vending_machine_check_expiry(self, _):
        self.check_expirys()
        self.engine.register_event_in(EXPIRY_CHECK_INTERVAL, self.tick_vending_machine_check_expiry, self, self)

    def alert_changes(self, previous_state, update_all = False):
        props = {}
        for a in alert_types:
            if update_all or ((a in previous_state) != (a in self.current_alerts)): # If this alert has changed
                props[a] = a in self.current_alerts
        return props

    def tick_alert_check(self, _):
        old_current_alerts = self.current_alerts.copy() # So we can detect changes
        for a in alert_types:
            if a not in self.current_alerts:    # Alert not active
                chance = float(ALERT_CHECK_INTERVAL)/alert_types[a]["mtbf"]
                if random.random() < chance:
                    self.current_alerts[a] = True
            else:                               # Alert active
                chance = float(ALERT_CHECK_INTERVAL)/alert_types[a]["average_length"]
                if random.random() < chance:
                    del self.current_alerts[a]

        props = self.alert_changes(old_current_alerts)
        if props != {}:
            props.update({"eventType" : "alert"})
            self.set_properties(props)
        self.engine.register_event_in(ALERT_CHECK_INTERVAL, self.tick_alert_check, self, self)

    # def tick_alert_cancel(self, _):
    #     self.current_alert = None
    #     self.set_property("alert", None)

    def tick_heartbeat(self, _):
        self.send_heartbeat_message()
        self.engine.register_event_in(HEARTBEAT_INTERVAL, self.tick_heartbeat, self, self)

    def check_expirys(self):
        has_expired = False
        will_expire_in_6_hrs = False
        now = self.engine.get_now()
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                if self.stock_level[r][c] > 0: 
                    prod = self.product_catalogue[self.product_number_in_position[r][c]]
                    if "lifetime" in prod:
                        lifetime = prod["lifetime"]
                        restocked = self.restock_time[r][c]
                        if restocked + lifetime < now:
                            has_expired = True
                        if restocked + lifetime - 6*60*60 < now:
                            will_expire_in_6_hrs = True
        if self.get_property_or_None("expired") != has_expired:
            pass # self.set_property("expired", has_expired)
        if self.get_property_or_None("expire_in_6_hrs") != will_expire_in_6_hrs:
            pass # self.set_property("expire_in_6_hrs", will_expire_in_6_hrs)

    def update_available_positions(self):
        avail_count = 0
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                    if self.get_level(r,c) > 0:
                        avail_count += 1
        if self.send_available_positions:
            self.set_property("positions_available", avail_count)

    def replenish(self):
        for r in range(self.machine_rows):
            for c in range(self.machine_columns):
                if self.past_sellby_date(r,c):
                    # self.set_property("event_log", "Disposed of expired food in "+self.position_name(r,c), always_send=True)
                    self.set_level(r,c, 0)
                if Vending_machine.myRandom.random() < 0.9:    # Chance of restocking any individual position 
                    if self.get_level(r,c) < MAX_STOCK_PER_POSITION:
                        # self.set_property("event_log", "Restocking "+self.position_name(r,c), always_send=True)
                        self.set_level(r,c, MAX_STOCK_PER_POSITION)
                        # self.set_property(self.position_name(r,c)+"_event_restock", True, always_send=True)
                        self.restock_time[r][c] = self.engine.get_now()
        self.update_available_positions()
        # self.set_property("event_log", "Emptying/restocking cashbox", always_send=True)
        old_cash = self.cashbox_cash()
        self.cashbox_initialise()
        new_cash = self.cashbox_cash()
        # self.set_property("cash_recovered", old_cash - new_cash, always_send=True)
        # self.set_property("event_replenish", True, always_send=True)
        # self.set_property("event_log", "Replenishment complete", always_send=True)
        self.send_replenish_message(old_cash - new_cash)
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
            pass # self.set_property("event_log", "Failed to make correct change. Change was " + str(value) + " but returned only "+str(bag_value(change)))
        return change

    def cashbox_cash(self):
        return bag_value(self.cashbox)

    def cashbox_update(self):
        # self.set_property("cashbox_cash", self.cashbox_cash())
        pass

    def accept_payment(self, price):
        # Work out what coins were provided to pay for the goods
        if Vending_machine.myRandom.random() >= CASH_LIKELIHOOD:  # Smartcard payment
            # self.set_property("vend_event_cashless", price, always_send=True)
            return "cashless"
        else:
            for biggest in range(len(CASH_DENOMINATIONS)):   # Find index of denomination that's big-enough to pay outright
                if CASH_DENOMINATIONS[biggest] >= price:
                    break
            if Vending_machine.myRandom.random() > 0.5:       # they just pay with a single unit of currency
                payment = { CASH_DENOMINATIONS[biggest] : 1 }
            else:                           # they make up the payment with coins
                payment = {}
                for i in range(biggest-1, -1, -1):
                    num = int((price-bag_value(payment)) / CASH_DENOMINATIONS[i])
                    if Vending_machine.myRandom.random() > 0.25:  # A chance that we don't have any smaller change, so we overpay with this denom
                        num += 1    # 
                    add_to_bag(payment, CASH_DENOMINATIONS[i], num)
                    if bag_value(payment) >= price:
                        break
            # self.set_property("vend_coins_accepted_total", bag_value(payment))
            add_bags(self.cashbox, payment)
            if bag_value(payment) != price:
                change = self.make_change(bag_value(payment) - price)
                # self.set_property("vend_change_issued", str(change))
            self.cashbox_update()
            return "cash"

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
    for (k,v) in bag.items():
        value += k * v
    return value

