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

        pysonar.addToPythonPath("tests/")

    def assertFirstInvoked(self, class_name, init_args, method_args):
        class_method_invocations = pysonar.getMethodInvocationInfo()[class_name]
        self.assertTrue(len(class_method_invocations) > 0, 'no method invocations of %s' % class_name)
        actual_init_args, actual_method_args, _, _ = class_method_invocations[0]
        
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

    def testAssignAttributeInInit(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            def __init__(self):
                self.attr = "simple"
        b = B()
        arg = b.attr
        A().method(arg)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testAssignAttributeAndInvokeMethod(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            def __init__(self, a):
                self.attr = a
        a = None
        a = A()
        b = B(a)
        a = b.attr.method('simple1')
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple1",)])

    def testPassActualParameterWithNameSelf(self):
        a = dedent("""
        class Test():
            def method(self, arg):
                return arg

        class Obj():
            def __init__(self, factory):
                self.factory = factory

        class Factory():
            # factory passes itself to the created objects
            def factoryMethod(self):
                return Obj(self)
            def test(self):
                Test().method('simple')

        obj = Factory().factoryMethod()
        obj.factory.test()
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("Test", [], [("simple",)])

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

    def testChainedAttribute(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            pass
        b = B()
        b.b = B()
        b.b.b = 'simple'
        A().method(b.b.b)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testAttributeAsArgument(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            pass
        b = B()
        b.attr = "simple"
        A().method(b.attr)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testInit(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            def __init__(self):
                self.attr = "simple"
        b = B()
        arg = b.attr
        A().method(arg)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testChainedAttributeCall(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            pass
        b = B()
        b.b = B()
        b.b.b = A()
        b.b.b.method("simple")
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

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

    def testImportWithClass(self):
        a = dedent("""
        import class_a
        class A():
            def method(self, arg):
                return arg
        a = class_a.a()
        A().method(a.attr)
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

    def testImportClassFrom(self):
        a = dedent("""
        from class_a import a
        class A():
            def method(self, arg):
                return arg
        object = a()
        A().method(object.attr)
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

    @skip("skip for now")
    def testImportWithConstant(self):
        a = dedent("""
        import defines_simple_constant_a
        class A():
            def method(self, arg):
                return arg
        A().method(defines_simple_constant_a.a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])


    def testCallMethodOfClass(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class Klass():
            def method(self, arg):
                A().method(arg)

        Klass.method(Klass(), 'simple')
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testCallParentMethod(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class Parent():
            def overridden(self, arg):
                A().method(arg)

        class Child(Parent):
            def overridden(self, arg):
                Parent.overridden(self, arg)

        Child().overridden('simple')
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("Child", [], [("simple",)])
        self.assertFirstInvoked("A", [], [("simple",)])

    def testOverrideParentMethod(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class Parent():
            def overridden(self, arg):
                pass

        class Child(Parent):
            def overridden(self, arg):
                A().method(arg)

        Child().overridden('simple')
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("Child", [], [("simple",)])
        self.assertFirstInvoked("A", [], [("simple",)])

    @skip('class attribute')
    def testClassAttribute(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class B():
            string = "simple"

        A().method(B.string)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])
        
    def testInheritanceChain(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class Base():
            def m(self):
                A().method("simple")
        class Child(Base): pass
        class ChildOfChild(Child): pass

        ChildOfChild().m()
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testInheritanceFromCallAttributeResult(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class Base():
            def get(self):
                return Base
            def m(self):
                A().method("simple")
        class Child(Base().get()): pass

        Child().m()
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testInheritanceFromUnknown(self):
        a = dedent("""
        a = unknown

        class Child(a): pass
        """)
        pysonar.checkString(a)

    @skip("")
    def testListSubscript(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = ['simple']
        A().method(a[0])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    @skip("")
    def testListAppend(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = []
        a.append('simple')
        A().method(a[0])
        """)
        pysonar.checkString(a)

    @skip("")
    def testDictSubscript(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = {'a': 'simple'}
        A().method(a['a'])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])


if __name__ == "__main__":
    unittest.main()
