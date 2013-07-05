'''
Created on Jul 5, 2013

@author: signalpillar
'''

import pysonar as ps
from tasty import as_unit, first_in_history


@as_unit
def test_dict(ut):
    s = '''
dict_ = {}
# for k, v in dict_.items():

# for k, v in dict_.iteritems()
# for k in dict_.keys()
# for k in dict_
# for v in dict_.values()

'''
    ps.checkString(s)

    result = first_in_history('result', ps)
    ut.assertTrue(isinstance(result, ps.ObjType))
    ut.assertEqual("module", result.classtype.name)