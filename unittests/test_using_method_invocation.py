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
            if isinstance(other, ast.Str):
                return self.s == other.s
            return NotImplemented
        def strHash(self):
            return hash(self.s)
        ast.Str.__hash__ = strHash
        def strLt(self, other):
            if isinstance(other, str):
                return self.s < other
            if isinstance(other, ast.Str):
                return self.s < other.s
            return NotImplemented
        ast.Str.__eq__ = strEquals
        ast.Str.__lt__ = strLt

        pysonar.addToPythonPath("tests/")

    def assertFirstInvoked(self, class_name, init_args, method_args):
        class_method_invocations = pysonar.getMethodInvocationInfo()[class_name]
        self.assertTrue(len(class_method_invocations) > 0, 'no method invocations of %s' % class_name)
        actual_init_args, actual_method_args, _, _ = class_method_invocations[0]
        
        self.assertItemsEqual(init_args, actual_init_args)
        self.assertItemsEqual(method_args, actual_method_args)

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

    def testMultipleAssignmentsInIf(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = 'a'
        if True:
            a = 'b'
        else:
            a = 'c'
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("c", "b")])

    def testTryExceptElse(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        try:
            a = 'simple'
        except:
            pass
        else:
            A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    @skip("")
    def testMultipleAssignmentsTryExcept(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = 'a'
        try:
            a = 'b'
        except:
            a = 'c'
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("b", "c")])

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

    @skip("")
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

    def testSelf(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class B():
            def a(self, arg):
                self.b(arg)

            def b(self, arg):
                A().method(arg)

        B().a('simple')
        """)
        pysonar.checkString(a)
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
        
    def testClassAttributeInDefaults(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg

        class B():
            string = "simple"
            def m(self, a=string):
                return a

        A().method(B.m())
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

    def testListSubscriptSlice(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = ['simple']
        b = a[:]
        A().method(b[0])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    @skip("")
    def testListSubscriptAssign(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = ['simple1']
        a[0] = 'simple2'
        A().method(a[0])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple1", "simple2")])

    def testListExtend(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = []
        a.extend(['simple'])
        A().method(a[0])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

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
        self.assertFirstInvoked("A", [], [("simple",)])

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

    def testRecurseInfiniteSubscript(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        def recurse(a):
            b = a[1]
            recurse(b)
        recurse([])
        """)
        pysonar.checkString(a)

    def testRecurseInfiniteUnknownAttr(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        def recurse(a):
            recurse(a.a)
        recurse(a)
        """)
        pysonar.checkString(a)

    def testDictSubscriptAssign(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = {'a': 'simpleA', 'b': 'simpleB'}
        a['a'] = 'simpleA2'
        a['b'] = 'simpleB2'
        A().method(a[unknown])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simpleB2","simpleB", "simpleA2","simpleA")])

    def testDictUpdate(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = {}
        a.update({'a': 'simpleA'})
        A().method(a['a'])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simpleA",)])

    def testDictSubscriptReAssign(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = {'a': 'simpleA'}
        a['a'] = 'simpleB'
        A().method(a['a'])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simpleA", "simpleB")])

    def testDictSubscriptAssignValues(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = {'a': 'simpleA'}
        a['a'] = 'simpleB'
        for b in a.values():
            A().method(b)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simpleA", "simpleB")])

    def testForInTuple(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = ('simple',)
        for b in a:
            A().method(b)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testFilter(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = filter(None, ('simple',))
        b = a[0]
        A().method(b)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testMap(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        def fun1(i):
            return 'simple'
        def fun2(i):
            return i
        a = map(fun1, ('',))
        a = map(fun2, a)
        b = a[0]
        A().method(b)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testReduce(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        l = []
        def append(a, b):
            l.append(a)
            return b
        reduce(append, ['a', 'b', 'c'])
        A().method(l[0])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [('a','b','c')])

    def testListSum(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        l = ['a'] + ['b'] + ['c']
        A().method(l[0])
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [('a','b','c')])

    def testClassScope(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        a = 'simple'
        class B():
            a = 'hard'

            def method(self):
                A().method(a)
        B().method()
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testObjectCall(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            def __call__(self):
                A().method('simple')
        B()()
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testStarArgs(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        def f(*args):
            A().method(args[0])
        f('simple')
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testStarArgsUnpackToVararg(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        def f(*args):
            A().method(args[0])
        a = ['simple']
        f(*a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testStarArgsUnpackToArgs(self):
        a = dedent("""
        class A():
            def method(self, arg):
                return arg
        class B():
            def m(self, arg):
                return arg
        a = ['simple']
        b = B().m(*a)
        A().method(b)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])

    def testCopyCopy(self):
        a = dedent("""
        import copy
        class A():
            def method(self, arg):
                return arg
        a = copy.copy("simple")
        A().method(a)
        """)
        pysonar.checkString(a)
        self.assertFirstInvoked("A", [], [("simple",)])


if __name__ == "__main__":
    unittest.main()
