'''
Created on Jul 5, 2013

@author: signalpillar
'''
import unittest
import pysonar as ps


class Test(unittest.TestCase):
    
    def test_in_union(self):
        u = [1, 2, 3, 4, 5]
        self.assertTrue(ps.inUnion(2, u))

    def test_remove_type(self):
        self.assertEqual([2, 3, 4, 5],
                         ps.removeType(1, [1, 2, 3, 1, 4, 5]))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_remove_type']
    unittest.main()