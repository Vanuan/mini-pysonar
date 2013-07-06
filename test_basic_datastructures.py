'''
Created on Jul 5, 2013

@author: signalpillar
'''

import pysonar as ps
from tasty import as_unit, first_in_history


@as_unit
def test_dict_initializator_literal(ut):
    'Dictionary literal support'
    s = '''
dict_ = {}
dict_2 = {1: 2,
          3: 4}
'''
    ps.checkString(s)
    ut.assertDict({}, first_in_history("dict_", ps))
    ut.assertDict({1: 2, 3: 4}, first_in_history("dict_2", ps))
    

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
        return dict_.get(k)
        
new_values = iter_over_dict_keys()
    '''

    ps.checkString(s)
    r = first_in_history('new_values', ps)
    ut.assertEqual(1, len(r)) 
    ut.assertNum(2, r[0])

# for k, v in dict_.items():

# for k, v in dict_.iteritems()
# for k in dict_.keys()
# for k in dict_
# for v in dict_.values()
