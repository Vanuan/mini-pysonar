import pysonar as ps
from tasty import first_in_history, PysonarTest


class Test(PysonarTest):

    def test_import_accessability_in_inner_context(self):
        s = '''
import objy

def x():
    return objy
        
result = x()
    '''
        ps.checkString(s)
        result = first_in_history('result', ps)
        self.assertTrue(isinstance(result, ps.ObjType))
        self.assertEqual("module", result.classtype.name)
    
    
    def test_import_module_with_class(self):
        # set up
        ps.addToPythonPath('tests')
    
        # exercise
        ps.checkString('import class_a')
    
        # verify
        result = first_in_history('class_a', ps)
        self.assertTrue(isinstance(result, ps.ObjType))
        self.assertTrue('a' in result.attrs.keys())
        self.assertTrue(isinstance(result.attrs['a'], list))
        self.assertTrue(1, len(result.attrs['a']))
        self.assertTrue(isinstance(result.attrs['a'][0], ps.ClassType))
    
    
    def test_import_module_with_func(self):
        # set up
        ps.addToPythonPath('tests')
    
        # exercise
        ps.checkString('import func_a')
    
        # verify
        result = first_in_history('func_a', ps)
        self.assertTrue(isinstance(result, ps.ObjType))
        self.assertTrue('a' in result.attrs.keys())
        self.assertTrue(isinstance(result.attrs['a'], list))
        self.assertTrue(1, len(result.attrs['a']))
        self.assertTrue(isinstance(result.attrs['a'][0], ps.Closure))
    
    
