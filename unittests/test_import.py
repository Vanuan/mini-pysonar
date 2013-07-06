import pysonar as ps
from tasty import as_unit, first_in_history
from nose.tools import nottest


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


@as_unit
def test_import_module_with_class(ut):
    # set up
    ps.addToPythonPath('tests')

    # exercise
    ps.checkString('import class_a')

    # verify
    result = first_in_history('class_a', ps)
    ut.assertTrue(isinstance(result, ps.ObjType))
    ut.assertTrue('a' in result.attrs.keys())
    ut.assertTrue(isinstance(result.attrs['a'], list))
    ut.assertTrue(1, len(result.attrs['a']))
    ut.assertTrue(isinstance(result.attrs['a'][0], ps.ClassType))


@as_unit
def test_import_module_with_func(ut):
    # set up
    ps.addToPythonPath('tests')

    # exercise
    ps.checkString('import func_a')

    # verify
    result = first_in_history('func_a', ps)
    ut.assertTrue(isinstance(result, ps.ObjType))
    ut.assertTrue('a' in result.attrs.keys())
    ut.assertTrue(isinstance(result.attrs['a'], list))
    ut.assertTrue(1, len(result.attrs['a']))
    ut.assertTrue(isinstance(result.attrs['a'][0], ps.Closure))

