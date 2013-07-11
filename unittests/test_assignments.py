import pysonar
from tasty import PysonarTest

class Test(PysonarTest):

    def test_simple_assignment(self):
        pysonar.checkFile("tests/assign.py")
    
    def test_attr_assignment(self):
        pysonar.checkFile("tests/assign_attribute.py")
