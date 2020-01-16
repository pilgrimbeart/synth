"""merge_test.py
Tests whether two posts can be safely merged without losing information
"""

def ok(post1, post2):
    if post1["$id"] != post2["$id"]:    # Different devices
        return False
    if post1["$ts"] != post2["$ts"]:    # Different times
        return False
    specials = set(["$id", "$ts"])
    x = set(post1.keys()) - specials
    y = set(post2.keys()) - specials
    return x & y == set([])             # Don't merge if it will cause properties to be overwritten (TODO: strictly it's OK to merge if the values are the same)

