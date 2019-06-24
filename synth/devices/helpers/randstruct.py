"""RANDSTRUCT
   Take a structured string and make random choices within it"""
#
# Copyright (c) 2019 DevicePilot Ltd.
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

import random, ast

def ev(x):
    if isinstance(x, list):     # Concatenate lists
        if len(x)==0:
            return None
        if len(x)==1:
            return x[0]      # Don't force things to be lists
        r = ""
        for e in x:
            r = r + ev(e) 
        return r
    if isinstance(x, tuple):    # Choose from tuples
        n = random.randrange(0, len(x))
        return ev(x[n])
    return x

def evaluate(s):
    a = ast.literal_eval(s)
    return ev(a)

if __name__ == "__main__":
    s = '[("I have","Everyone has"),(" good"," bad")," things to say",("",[" to you",(""," boyo")])]'
    for i in range(10):
        print(evaluate(s))
    s = '(1,2,3,4,5)'
    for i in range(10):
        print(evaluate(s))
