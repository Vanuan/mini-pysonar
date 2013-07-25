'''
Created on Jul 5, 2013

@author: signalpillar
'''
import unittest
import pysonar as ps
import lists
from lists import LinkedList as P, nil
import ast
import pysonar
from textwrap import dedent


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


class TestAttributeInference(unittest.TestCase):
    def getEnv(self, string):
        module_body = pysonar.createAST(string).body
        _, env = pysonar.inferSeq(module_body, pysonar.close(module_body, nil), nil)
        return env

    def assertString(self, value, inferred_type):
        self.assertEqual(pysonar.Str, inferred_type.__class__)
        self.assertEqual(value, inferred_type.s)

    def assertClass(self, name, inferred_type):
        self.assertEqual(pysonar.ClassType, inferred_type.__class__)
        self.assertEqual(name, inferred_type.name)

    def assertInstanceMethod(self, method_name, class_name, inferred_type):
        self.assertEqual(pysonar.AttrType, inferred_type.__class__)
        self.assertEqual(method_name, inferred_type.clo[0].func.name)

    def testInferAttribute(self):
        # setup
        env = self.getEnv(dedent('''
        class A:
            pass
        class B:
            pass
        a = A()
        a.b = B()
        a.b.c = 'simple'
        '''))

        # exercise attribute inference (and assignment)
        attr = pysonar.createAST('a.b.c').body[0].value
        inferred = pysonar.infer_attribute(attr, env, nil)

        # verify
        self.assertEqual(1, len(inferred))
        self.assertString('simple', inferred[0])

    def testInferInstanceMethod(self):
        # setup
        env = self.getEnv(dedent('''
        class A:
            def method(self):
                pass
        a = A()
        '''))

        # exercise instance method creation and inference
        attr = pysonar.createAST('a.method').body[0].value
        inferred = pysonar.infer_attribute(attr, env, nil)

        # verify
        self.assertEqual(1, len(inferred))
        self.assertInstanceMethod('method', 'A', inferred[0])



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_remove_type']
    unittest.main()
