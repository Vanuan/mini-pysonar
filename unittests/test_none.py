'''
Created on Jul 10, 2013

@author: iyani
'''
import unittest
from tasty import PysonarTest
import pysonar
from pysonar import PrimType


class Test(PysonarTest):

    def testNone(self):
        pysonar.checkString('def fun():\n    return None\na = fun()')
        
        a = self.first_in_history('a')
        self.assertEqual((PrimType(None),), a)

    def testImplicitNone(self):
        pysonar.checkString('def fun():\n    return\na = fun()')
        
        a = self.first_in_history('a')
        self.assertEqual((PrimType(None),), a)


if __name__ == "__main__":
    unittest.main()
