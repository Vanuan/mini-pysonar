'''
Created on Jul 5, 2013

@author: signalpillar
'''
import unittest
import pysonar as ps
import lists
from lists import LinkedList as P, nil


class TestOperationsOnList(unittest.TestCase):

    def test_slits(self):
        self.assertEqual(P(1, P(2, P(3, nil))), lists.slist([1, 2, 3]))


class TestListType(unittest.TestCase):

    def test_equality(self):
        l1 = lists.slist([1, 2, 3])
        l2 = lists.slist([1, 2, 3])
        self.assertEqual(l1, l2)


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
