class B:
    pass

b = B()


class WithInit:
    
    def __init__(self, p, p2):
        self.p = p
        self.p1 = p2
        
    def x(self):
        return WithInit.__init__(self, 3, 42);

with_init = WithInit(1, 2)
with_init.x(with_init)