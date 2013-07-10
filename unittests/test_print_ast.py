'''
Created on Jul 10, 2013

@author: iyani
'''
import unittest
import pysonar
from tasty import PysonarTest


class Test(PysonarTest):

    def testShouldPrintFilename(self):
        pysonar.checkString('a = 1\nb = 1')
        b = self.first_in_history('b')
        self.assertEqual(str(b), '[1@<string>:2]')


if __name__ == "__main__":
    unittest.main()
