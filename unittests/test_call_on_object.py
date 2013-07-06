'''
Created on Jul 4, 2013

'''
import pysonar as ps
from tasty import as_unit, find_in_history


@as_unit
def test_bound_method_call_and_obj_new_attr_creation(ut):
    s = '''
class B:
    def x(self, p):
        self.p = p
        return self
        
new_b = B().x(2)
    '''
    ps.checkString(s)

    class_types = find_in_history('B', ps)
    ut.assertEqual(1, len(class_types))
    class_type = class_types[0]
    ut.assertEqual('B', class_type.name)
    ut.assertEqual(1, len(class_type.attrs))
    
    clo = class_type.attrs.get('x')
    ut.assertTrue(isinstance(clo, ps.Closure))
    ut.assertEqual([], clo.defaults)
    
    # assert new instance
    values = find_in_history("new_b", ps)
    ut.assertEqual(1, len(values))
    new_b = values[0]
    ut.assertTrue(isinstance(new_b, ps.ObjType))
    ut.assertEqual(2, new_b.attrs.get("p")[0].n)

    
     
@as_unit
def test_obj_initialized_without_explicit_init_call(ut):
    s = '''
class B:
    pass
 
b = B()
'''
    ps.checkString(s)
    class_types = find_in_history('B', ps)
    ut.assertEqual(1, len(class_types))
    class_type = class_types[0]
    ut.assertEqual('B', class_type.name)
    ut.assertEqual(0, len(class_type.attrs))
 

@as_unit
def test_object_initialized_by_calling_class_obj_as_attribute(ut):
    s = '''
class B:
    pass
 
b = B()
b.x = B
 
b_inst = b.x()
    '''
    ps.checkString(s)

    b_insts = find_in_history('b_inst', ps)
    ut.assertEqual(1, len(b_insts))
    b_inst = b_insts[0]
    
    # check count of attributes on new instance of B, must be x

    # assert type of new instance
    ut.assertTrue(isinstance(b_inst, ps.ObjType))
    
    # assert class of new instance
    b_cls = find_in_history('B', ps)
    ut.assertEqual(1, len(b_cls))
    B = b_cls[0]
    
    # assert class type 
    ut.assertEqual(B, b_inst.classtype)
     
     
@as_unit
def test_simple_init_call_where_self_arg_required(ut):
    s = '''
 
class WithInit:
     
    def __init__(self, p, p2):
        self.p = p
        self.p1 = p2
         
    def z(self):
        return WithInit(3, 42);
        
    def knows_about_fn_from_module(self):
        y = module_fn()
        return y
        
 
with_init = WithInit(1, 2)
with_init.z()

def module_fn():
    return 20
    
result_from_module_fn = with_init.knows_about_fn_from_module()
'''
    ps.checkString(s)
 
    with_inits = find_in_history('with_init', ps)
    ut.assertEqual(1, len(with_inits))
    with_init = with_inits[0]
    # assert type of new instance
    ut.assertTrue(isinstance(with_init, ps.ObjType))
    ut.assertEqual(5, len(with_init.attrs))
    ut.assertEqual(1, with_init.attrs.get("p")[0].n)
    ut.assertEqual(2, with_init.attrs.get("p1")[0].n)
    # assert class type
    cls = find_in_history('WithInit', ps)
    ut.assertEqual(1, len(cls))
    Cls = cls[0]
    # assert class type 
    ut.assertEqual(Cls, with_init.classtype)
    
    
    results = find_in_history('result_from_module_fn', ps)
    ut.assertEqual(1, len(results))
    result = results[0]
    # assert class type 
    ut.assertEqual(20, result.n)
    

 
@as_unit
def test_bound_call_with_actual_kwargs_returned(ut):
    c = '''
class A:
    def m(self, **kwargs):
        return kwargs
 
a = A()
result = a.m(keyarg='100')
    '''
    ps.checkString(c)
    results = find_in_history('result', ps)

    ut.assertEqual(1, len(results))
    result_as_pair = results[0].dict
    ut.assertEquals('keyarg', result_as_pair.fst.fst)
    ut.assertEquals('100', result_as_pair.fst.snd[0].s)
    result_as_pair.fst


@as_unit
def test_bound_call_with_actual_keywords_returned(ut):
    c = '''
class A:
    def m(self, default_x=100, y=200):
        return default_x, y
 
a = A()
result = a.m(100, 200)
result2 = a.m(100, y=200)
result3 = a.m(default_x=100)
    '''
    ps.checkString(c)
    results = find_in_history('result', ps)

#     ut.assertEqual(1, len(results))
#     result_as_pair = results[0].dic
#     ut.assertEquals('keyarg', result_as_pair.fst.fst)
#     ut.assertEquals('100', result_as_pair.fst.snd[0].s)
#     result_as_pair.fst