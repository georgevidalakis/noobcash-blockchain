import wrapt
import numpy as np

import threading

lock = threading.RLock()

class Test:

    def __init__(self):
        self.a = 0
    
    @wrapt.synchronized(lock)
    def inc1(self):
        for _ in range(int(5e8)):
            self.a += 1
    
    @wrapt.synchronized(lock)
    def inc2(self):
        for _ in range(int(5e8)):
            self.a += 1

    def show(self):
        print(self.a)


