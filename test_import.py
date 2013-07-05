import pysonar as ps
from tasty import as_unit, first_in_history


@as_unit
def test_import_accessability_in_inner_context(ut):
    s = '''
import objy

def x():
    return objy
        
result = x()
'''
    ps.checkString(s)
    result = first_in_history('result', ps)
    ut.assertTrue(isinstance(result, ps.ObjType))
    ut.assertEqual("module", result.classtype.name)