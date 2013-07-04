class TheClass:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        
def m():
    return 5

TheClass.class_level_attr = 4
TheClass.class_level_method = m()

class A():
    def m(self, a):
        return a
    
    
class X():
    pass

class Z():
    pass

z = Z()
    
a = A()
a.m(TheClass.class_level_attr)
a.m(TheClass.class_level_method)

a.b = X()
a.b.c = z

a.m(a.b)
a.m(a.b.c)

li = [1, 2, 3]
li[0] = 5

# inst = TheClass(1, 2)
# inst.inst_level_attr = 2
# 
# x = TheClass(1, 2)