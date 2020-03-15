import wrapt
import numpy as np

import threading

lock = threading.RLock()

class Test:

    def __init__(self):
        self.a = 0
    
    @wrapt.synchronized(lock)
    def inc(self, recurse : bool):
        self.a += 1
        if recurse:
            self.inc(False)

    def show(self):
        print(self.a)


