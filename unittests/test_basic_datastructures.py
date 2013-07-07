'''
Created on Jul 5, 2013

@author: signalpillar
'''

import pysonar as ps
from tasty import as_unit, first_in_history, find_in_history, PysonarTest, ut


@as_unit
def test_list_literal(ut):
    'List literal support'
    s = '''
the_list = []

non_empty_list = [1, 2, 3]
string_list = ["a", "b", "c"]

x = "20"
list_with_infering_involved = [1, "b", x]
'''
    ps.checkString(s)
    ut.assertList([], first_in_history("the_list", ps))
    ut.assertList([1, 2, 3], first_in_history("non_empty_list", ps))
    ut.assertList(["a", "b", "c"], first_in_history("string_list", ps))
    ut.assertList([1, "b", "20"], first_in_history("list_with_infering_involved", ps))


@as_unit
def test_dict_initializator(ut):
    'Dictionary literal support'
    s = '''
dict_ = {}
dict_2 = {1: 2,
          3: 4}
          
dict_3 = {1: 2,
          3: dict_2}
'''
    ps.checkString(s)
    ut.assertDict({}, first_in_history("dict_", ps))
    ut.assertDict({1: 2, 3: 4}, first_in_history("dict_2", ps))

    dict_3 = first_in_history("dict_3", ps)
    ut.assertSubDict({1: 2}, dict_3)
    ut.assertDictValueAsDict({1: 2, 3: 4}, dict_3, 3)

    
@as_unit
def test_list_iteration(ut):    
    s = '''
l1 = [1, 2, 3]

def iter_over_list():
    for e in l1:
        return e

r = iter_over_list()


def iter_over_list2():
    for e in list(l1):
        return e


r2 = iter_over_list2()
    '''
    ps.checkString(s)
    r = find_in_history('r', ps)
    ut.assertNums([1, 2, 3], r[0:3])
    ut.assertCont(r[3])

    r = find_in_history('r2', ps)
    # unknown type due to unknown list function
    ut._assertType(TypeError, r[0])


@as_unit
def _test_dict_iteration_by_keys(ut):
    '''
    Support the simplest iteration over dictionary
    
       For(target=Name(id='k', ctx=Store()),
           iter=Name(id='dict_', ctx=Load()),
           body=[Assign(targets=[Name(id='value', ctx=Store())],
                        value=Call(
                            func=Attribute(value=Name(id='dict_', ctx=Load()),
                                           attr='get', ctx=Load()),
                                           args=[Name(id='k', ctx=Load())],
                                           keywords=[],
                                           starargs=None,
                                           kwargs=None))],
           orelse=[]) '''
    s = '''
dict_ = {1: 2, 3: 4}

def iter_over_dict():
    values = []
    for k in dict_:
        value = dict_.get(k)
        values.append(value)
    return values
        
iter_over_dict()
    '''
    ps.checkString(s)
    
    
@as_unit
def test_dict_iteration_by_keys_using_explicit_call_to_keys_method(ut):
    '''
    Support the simplest case - one iteration over dictionary using explicit keys() call

    For(target=Name(id='k', ctx=Store()),
        iter=Call(func=Attribute(value=Name(id='dict_', ctx=Load()),
                  attr='keys', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=None),
                  body=[...], orelse=[]) 
    '''
    s = '''
dict_ = {1: 2, 3: 4}

def iter_over_dict_keys():
    for k in dict_.keys():
        # which element returned is undefined
        # (actually, it is defined by the order in which keys are iterated,
        #  which in turn is defined by the hash function, but it's
        #  too complicated)
        # we'll assume that any value can be returned
        return dict_.get(k)

new_values = iter_over_dict_keys()
    '''

    ps.checkString(s)
    r = find_in_history('new_values', ps)
    ut.assertEqual(3, len(r))
    ut.assertNums([2, 4], r[0:2])
    ut.assertCont(r[2])  # represents implicitly returned None

# for k, v in dict_.items():

# for k, v in dict_.iteritems()
# for k in dict_.keys()
# for k in dict_
# for v in dict_.values()


def test_huge_dict():
    ps.addToPythonPath('tests')
    # exercise
    ps.checkString('import huge_dict')

    # should not crash


def test_dict_default_value():
    # exercise
    ps.checkString('a = {"a": 1}; b = a.get("b", 2);')

    # verify
    r = find_in_history('b', ps)
    ut.assertEqual(2, len(r))
    ut.assertNums([1, 2], r)

def test_unhashable_dict_key():
    # exercise
    ps.checkString('''a = {b: 1}
for key, value in a.iteritems():
    pass''')


def test_tuple_unpack():
    # exercise
    ps.checkString('''a = {1: 2, 3: 4}
for key, value in a.iteritems():
    b = key
    c = value''')

    # verify
    r = find_in_history('key', ps)
    ut.assertEqual(2, len(r))
    ut.assertNums([1, 3], r)

    r = find_in_history('value', ps)
    ut.assertEqual(2, len(r))
    ut.assertNums([2, 4], r)

