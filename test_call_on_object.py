'''
Created on Jul 4, 2013

'''
import pysonar

 
def test_bound_method_call():
    s = '''
class B:
    def x(self, p):
        x.p = p
        
new_b = B().x(2)
    '''
    pysonar.checkString(s)
    
    
def test_obj_initialized_without_explicit_init_call():
    s = '''
class B:
    pass

b = B()
'''
    pysonar.checkString(s)
    

def _test_object_initialized_by_calling_class_obj_as_attribute():
    s = '''
class B:
    pass

b = B()
b.x = B

# unsupported
b.x()
    '''
    pysonar.checkString(s)
    
def test_simple_init_call_where_self_arg_required():
    s = '''

class WithInit:
    
    def __init__(self, p, p2):
        self.p = p
        self.p1 = p2
        
    def x(self):
        return WithInit.__init__(self, 3, 42);

with_init = WithInit(1, 2)
with_init.x()
'''
    pysonar.checkString(s)

def test_simple_bound_call():
    c = '''
class A:
    def m(self, x):
        self.m = x

a = A()
new_value = a.m(10)
    '''
    pysonar.checkString(c)

def test_bound_call_with_kwargs():
    c = '''
class A:
    def m(self, **kwargs):
        pass

a = A()
a.m(keyarg='')
    '''
    pysonar.checkString(c)
