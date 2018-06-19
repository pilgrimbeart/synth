# Tables.py
#
# Reads-in simple tables containing e.g. mappings, or histograms of distribution, and looks things up in them
# Currently only supports 2-column numeric .csv files
#
# table.find_fraction() - assuming that the table is (histogram bins, histogram values), then given a
#                         fraction from 0..1, this finds the row where the sum of column 2 achieves that fraction
#                         and returns the column 1 value (interpolated if necessary)
#                         This can be used for example for returning a value according to a weighted distribution.
#                         E.g. using random() to pick from a realistic distribution of cellular signal strengths
# table.lookup()        - find an entry in column 1 of a table and return corresponding column 2 value
#                        (interpolated if necessary)
#                         E.g. given a signal strength, find the corresponding uptime

import csv

class table():
    def __init__(self, read_file):
        lines = csv.reader(open(read_file, 'rb'))
        self.the_table = []
        self.column1_sum = 0.0
        self.cum_sum = []
        for line in lines:
            if line[0].startswith("#"):
                continue    # Ignore comments
            assert len(line) == 2, read_file + ": can only support tables with two columns"
            line[0] = float(line[0])
            line[1] = float(line[1])
            self.the_table.append(line)
            self.column1_sum += line[1]
            self.cum_sum.append(self.column1_sum)    # The cumulative sum INCLUDING this row
            # print line[0], line[1], self.column1_sum
        self.cum_sum = [x/self.cum_sum[-1] for x in self.cum_sum]   # Renormalise

    def lookup(self, v):    # Find v in column 1 and return column 2. If necessary, linear-interpolate.
        if v <= self.the_table[0][0]:   # Querying before start of table
            return self.the_table[0][1]
        if v >= self.the_table[-1][0]:   # Querying after end of table
            return self.the_table[-1][1]
        prev = self.the_table[0]
        for row in self.the_table[1:]:  # Find right pair of points
            if (v >= prev[0]) and (v <= row[0]):
                frac = (row[0] - v) / (row[0] - prev[0])
                return prev[1] * frac + row[1] * (1-frac)   # Linear interpolation
            prev = row

    def find_fraction(self, fraction):    # Sum column 2 until it equals the (normalised) fraction, then return column 1
        if fraction <= 0.0:
            return self.the_table[0][0]
        if fraction >= 1.0:
            return self.the_table[-1][0]
        if fraction <= self.cum_sum[0]:
            return self.the_table[0][0]
        for i in range(1, len(self.the_table)):
            # print "exploring range from ",self.the_table[i-1],"to",self.the_table[i]
            if self.cum_sum[i] > fraction:
                frac = (self.cum_sum[i] - fraction) / (self.cum_sum[i] - self.cum_sum[i-1])
                # print "frac=",frac
                return self.the_table[i-1][0] * (frac) + self.the_table[i][0] * (1-frac)

if __name__ == "__main__":
    def test(fn, value, desired=None):
        v = fn(value)
        print value,":", v
        if desired:
            assert abs((v-desired)/desired) < 0.01

    t = table("../../scenarios/cellular_signal_strength_histogram.csv")
    print open("../../scenarios/cellular_signal_strength_histogram.csv","rt").readlines()
    print "Testing lookup()"
    test(t.lookup, -103, 32)
    test(t.lookup, -102, 57)
    test(t.lookup, -101, 82)
    test(t.lookup, -100, 113.5)
    test(t.lookup, -1000, 9)
    test(t.lookup, 0, 29)
    test(t.lookup, 1000, 29)

    print "testing find_fraction()"
    test(t.find_fraction, -0.1, -105)
    test(t.find_fraction, 0.0, -105)
    test(t.find_fraction, 1.0, -47)
    test(t.find_fraction, 1.1, -47)
    test(t.find_fraction, 0.000001, -105)
    test(t.find_fraction, 0.001, -105)
    test(t.find_fraction, 0.006, -103)
    test(t.find_fraction, 0.007, -102.7)
    test(t.find_fraction, 0.1, -95)
    test(t.find_fraction, 0.741, -73)
    test(t.find_fraction, 0.963, -57)
    test(t.find_fraction, 0.996)
    test(t.find_fraction, 0.999999)
    
    print "All tests passed"

