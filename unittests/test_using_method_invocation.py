'''
Created on Jul 12, 2013

@author: iyani
'''
import unittest
import pysonar
from textwrap import dedent
import ast
from unittest.case import skip

class TypeErr:
    def __eq__(self, other):
        if isinstance(other, TypeError):
            return True
        return NotImplemented


class Test(unittest.TestCase):

    def setUp(self):
        # override AST primitive types comparison for tests
        def numEquals(self, other):
            if isinstance(other, int):
                return self.n == other
            return NotImplemented
        ast.Num.__eq__ = numEquals
        def strEquals(self, other):
            if isinstance(other, str):
                return self.s == other
            return NotImplemented
        ast.Str.__eq__ = strEquals

    def assertFirstInvoked(self, class_name, init_args, method_args):
        class_method_invocations = pysonar.getMethodInvocationInfo()[class_name]
        actual_init_args, actual_method_args, _ = class_method_invocations[0]
        
        self.assertEqual(init_args, actual_init_args)
        self.assertEqual(method_args, actual_method_args)

    def testSimpleConstant(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        A().method("simple", "simple")
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",), ("simple",)])

    def testAssignedVar(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = "simple"
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testAssignFunctionReturn(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        def foo(arg):
            return arg
        a = foo("simple")
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testFunctionCallAsArgument(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        def foo(arg):
            return arg
        A().method(foo("simple"))
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testAssignMethod(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            def foo(self, arg):
                return arg
        a = B().foo("simple")
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testMethodCallAsArgument(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            def foo(self, arg):
                return arg
        A().method(B().foo("simple"))
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testAssignAttribute(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            pass
        b = B()
        b.attr = "simple"
        arg = b.attr
        A().method(arg)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testAssignClass(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a_alias = A
        A().method("simple")
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    @skip("Bug")
    def testMultipleAssignments(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = None
        if True:
            a = 'a'
        else:
            a = 'b'
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [(pysonar.PrimType(None), "a", "b")])

    def testBasicInheritance(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class Base():
            def simple(self):
                return "simple"
        class Child(Base):
            pass
        a = Child().simple()
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testStrFormatting(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = "simple%s" % ""
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testStrFormattingUnsupported(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = "simple%s%s" % ("", "")
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple%s%s",)])


if __name__ == "__main__":
    unittest.main()
