#!/usr/bin/env python
#
# UTILS
#
# Copyright (c) 2017 DevicePilot Ltd.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import hashlib

def hashIt(n, limit):
    """Given a number or a string, return a non-obviously-correlated number [0..limit)."""
    if type(n)==int:
        x = n * 19079 # Prime
        x = (int(str(x)[::-1])) # Reverse its string representation
        n = n ^ x
        n = (n * 7919)  # Prime
        n = n % limit
        return n
    else:
        return abs(hash(n)) % limit
    

def consistent_hash(s):
    """Return a float 0..1 based on a string, consistently (Python's hash() is intentionally not consistent between runs!)"""
    if s is None:
        s = ""
    return int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16) % 10**8 / 10**8.0
