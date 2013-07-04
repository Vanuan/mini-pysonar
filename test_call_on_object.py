'''
Created on Jul 4, 2013

'''
import pysonar

 
def test_simple_assignment():
    #pysonar.checkFile("tests/assign_attribute.py")
    pysonar.checkFile("tests/bound_methods.py")

def test_attr_assignment():
    #pysonar.checkFile("tests/assign_attribute.py")
    pysonar.checkFile("tests/call_init.py")
