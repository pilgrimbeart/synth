"""merge_test.py
Tests whether two posts can be safely merged without losing information.
This means that either they are updating different properties.
Or they are updating the same property, but to the same value.
"""

import logging

def ok(post1, post2):
    if post1["$id"] != post2["$id"]:    # Different devices
        return False
    if post1["$ts"] != post2["$ts"]:    # Different times
        return False

    # Tried to find a way to avoid iteration, but Python doesn't do dict intersections 
    for (k,v) in post1.items():
        if k in post2:
            if post2[k] != v:
                return False

    return True

    # specials = set(["$id", "$ts"])
    # x = set(post1.keys()) - specials
    # y = set(post2.keys()) - specials
    # result = (x & y == set([]))            # Don't merge if it will cause properties to be overwritten (TODO: strictly it's OK to merge if the values are the same)

ALL_TESTS_PASSED = True

def test(x,y, should_be_true):
    global ALL_TESTS_PASSED

    result = ok(x,y)
    success = ["FAIL","PASS"][result==should_be_true]
    print("%-80s %-80s" % (x,y),":",ok(x,y), "-", success)
    if result!=should_be_true:
        ALL_TESTS_PASSED = False

if __name__ == "__main__":
    test({"$id":"1", "$ts":2},                  {"$id":"2", "$ts":2}, False)
    test({"$id":"1", "$ts":2},                  {"$id":"1", "$ts":1}, False)
    test({"$id":"1", "$ts":2},                  {"$id":"1", "$ts":2}, True)
    test({"$id":"1", "$ts":2, "a" : 1},         {"$id":"1", "$ts":2, "b" : 1}, True)
    test({"$id":"1", "$ts":2, "a" : 1},         {"$id":"1", "$ts":2, "a" : 1}, True)
    test({"$id":"1", "$ts":2, "a" : 1},         {"$id":"1", "$ts":2, "a" : 1, "b" : 2}, True)
    test({"$id":"1", "$ts":2, "a" : 1},         {"$id":"1", "$ts":2, "a" : 2}, False)
    test({"$id":"1", "$ts":2, "a" : 1},         {"$id":"1", "$ts":2, "a" : 2, "b" : 3}, False)
    
    if ALL_TESTS_PASSED:
        print("All tests passed")
    else:
        print("Tests FAILED")
