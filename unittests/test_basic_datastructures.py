'''
Created on Jul 5, 2013

@author: signalpillar
'''

import pysonar as ps
from tasty import first_in_history, find_in_history, PysonarTest
from pysonar import contType


class Test(PysonarTest):
    
    def test_list_literal(self):
        'List literal support'
        s = ('''the_list = []\n'''
             '''non_empty_list = [1, 2, 3]\n'''
             '''string_list = ["a", "b", "c"]\n'''
             '''x = "20"\n'''
             '''list_with_infering_involved = [1, "b", x]\n''')

        ps.checkString(s)
        self.assertList([], first_in_history("the_list", ps))
        self.assertList([1, 2, 3], first_in_history("non_empty_list", ps))
        self.assertList(["a", "b", "c"], first_in_history("string_list", ps))
        self.assertList([1, "b", "20"], first_in_history("list_with_infering_involved", ps))
    

    def test_list_of_lists(self):
        s = ('''def fun(): return [[1, 2]]\nthe_list = fun()''')

        ps.checkString(s)
        self.assertList(((1,2),), first_in_history("the_list", ps))

    
    def test_dict_initializator(self):
        'Dictionary literal support'
        s = ('dict_ = {}\n'
             'dict_2 = {1: 2, 3: 4}\n'
             'dict_3 = {1: 2, 3: dict_2}')

        ps.checkString(s)
        self.assertDict({}, first_in_history("dict_", ps))
        self.assertDict({1: 2, 3: 4}, first_in_history("dict_2", ps))
    
        dict_3 = first_in_history("dict_3", ps)
        self.assertSubDict({1: 2}, dict_3)
        self.assertDictValueAsDict({1: 2, 3: 4}, dict_3, 3)
    
        
    def test_list_iteration(self):    
        s = (
            'l1 = [1, 2, 3]\n'
            'def iter_over_list():\n'
            '    for e in l1:\n'
            '        return e\n'
            'r = iter_over_list()\n'
            'def iter_over_list2():\n'
            '    for e in list(l1):\n'
            '        return e\n'
            'r2 = iter_over_list2()\n'
            )

        ps.checkString(s)
        r = find_in_history('r', ps)
        self.assertNums([1, 2, 3], r, cont=True)
    
        r = find_in_history('r2', ps)
        # unknown type due to unknown list function
        self.assertList([TypeError], r, cont=True)
    
    
    def _test_dict_iteration_by_keys(self):
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
        
        
    def test_dict_iteration_by_keys_using_explicit_call_to_keys_method(self):
        '''
        Support the simplest case - one iteration over dictionary using explicit keys() call
    
        For(target=Name(id='k', ctx=Store()),
            iter=Call(func=Attribute(value=Name(id='dict_', ctx=Load()),
                      attr='keys', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=None),
                      body=[...], orelse=[]) 
        '''
        s = ('dict_ = {1: 2, 3: 4}\n'
            'def iter_over_dict_keys():\n'
            '    for k in dict_.keys():\n'
                    # which element returned is undefined
                    # (actually, it is defined by the order in which keys are iterated,
                    #  which in turn is defined by the hash function, but it's
                    #  too complicated)
                    # we'll assume that any value can be returned
            '        return dict_.get(k)\n'
            'new_values = iter_over_dict_keys()')

        ps.checkString(s)
        r = find_in_history('new_values', ps)
        self.assertEqual(3, len(r))
        self.assertNums([2, 4], r, cont=True)
        #self.assertCont(r[2])  # represents implicitly returned None
    
    # for k, v in dict_.items():
    
    # for k, v in dict_.iteritems()
    # for k in dict_.keys()
    # for k in dict_
    # for v in dict_.values()
    
    
    def test_huge_dict(self):
        ps.addToPythonPath('tests')
        # exercise
        ps.checkString('import huge_dict')
    
        # should not crash
    
    
    def test_dict_default_value(self):
        # exercise
        ps.checkString('a = {"a": 1}; b = a.get("b", 2);')
    
        # verify
        r = find_in_history('b', ps)
        self.assertEqual(2, len(r))
        self.assertNums([1, 2], r)
    
    def test_unhashable_dict_key(self):
        # exercise
        ps.checkString('''a = {b: 1}\n'''
                       '''for key, value in a.iteritems():\n'''
                       '''    pass''')
    
    
    def test_tuple_unpack(self):
        # exercise
        ps.checkString('''a = {1: 2, 3: 4}\n'''
                       '''for key, value in a.iteritems():\n'''
                       '''    b = key\n'''
                       '''    c = value\n''')
    
        # verify
        r = find_in_history('key', ps)
        self.assertEqual(2, len(r))
        self.assertNums([1, 3], r)
    
        r = find_in_history('value', ps)
        self.assertEqual(2, len(r))
        self.assertNums([2, 4], r)
    
