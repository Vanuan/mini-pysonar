import unittest

__unittest = True
import ast
import pysonar as ps
import functools
import lists


class VisitorByType:
    
    def generic_visit(self, node):
        class_name = node.__class__.__name__
        raise NotImplementedError("Visit method for the %s is not implemented" % class_name)

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)


class GetNodeValue(VisitorByType):
    
    def visit_Num(self, node):
        return node.n
    
    def visit_Str(self, node):
        return node.s

    def visit_str(self, node):
        return node
    
    def visit_list(self, lst):
        return [self.visit(l) for l in lst]
    
    def visit_tuple(self, tu):
        return tuple(self.visit_list(tu))


_get_value = GetNodeValue().visit


def flatten(list_):
    "@types: iterable[T] -> list[T]"
    r = []
    for nest_list in list_:
        r.extend(nest_list)
    return r


def get_dict_with_flattened_values(dict_):
    '@types: DictType -> dict'
    r = {}
    for p in dict_.dict:
        r[_get_value(p.fst)] = _get_value(p.snd)[0]
    return r


class PysonarTest(unittest.TestCase):

    def runTest(self):
        pass

    def _assertType(self, expected_type, actual_value):
        if not isinstance(actual_value, expected_type):
            raise AssertionError("Expected type %s but got %s(%s)" %
                                 (expected_type, type(actual_value),
                                 actual_value))

    def assertNum(self, expected, actual):
        self._assertType(ast.Num, actual)
        self.assertEqual(expected, actual.n)

    def assertNums(self, expecteds, actuals):
        for actual in actuals:
            self._assertType(ast.Num, actual)
        actuals = sorted([num.n for num in actuals])
        self.assertEqual(sorted(expecteds), actuals)

    def assertCont(self, expected):
        self.assertEqual(ps.contType, expected)

    def assertList(self, expected, actual):
        '@types: dict, pysonar.ListType'
        self._assertType(ps.ListType, actual)
        actual = actual.elts
        self.assertEqual(len(expected), lists.length(actual), "Size mismatch")
        for i, actual_value in enumerate(actual):
            self.assertEqual(expected[i], _get_value(actual_value),
                         "Different values at index: %s" % i)

    def assertDict(self, expected, actual):
        '@types: dict, pysonar.DictType'
        self._assertType(ps.DictType, actual)
        actual = actual.dict
        self.assertEqual(len(expected), lists.length(actual), "Size mismatch")
        for item_pair in actual:
            key, values = item_pair.fst, item_pair.snd
            actual_key = _get_value(key)
            actual_value = _get_value(values[0])
            self.assertEqual(expected.get(actual_key), actual_value,
                         "Value for key '%s': %s != %s, " % (actual_key,
                                                 expected.get(actual_key),
                                                 actual_value))

    # TODO how is this different from assertSubDict?
    def assertSubDict(self, expected, actual):
        '@types: dict, pysonar.DictType'
        self._assertType(ps.DictType, actual)
        actual = actual.dict
        for item_pair in actual:
            key, values = item_pair.fst, item_pair.snd
            actual_key = _get_value(key)
            if actual_key in expected:
                actual_value = _get_value(values[0])
                self.assertEqual(expected.get(actual_key), actual_value,
                             "Different values for the same key: %s" % actual_key)

    def assertDictValueAsDict(self, expected, actual_dict, actual_key):
        self._assertType(ps.DictType, actual_dict)
        actual = actual_dict.dict
        for item_pair in actual:
            key, values = item_pair.fst, item_pair.snd
            if actual_key == _get_value(key):
                actual_value = values[0]
                self._assertType(ps.DictType, actual_value)
                self.assertEqual(expected, get_dict_with_flattened_values(actual_value),
                             "Different values for the same key: %s" % actual_key)
                return
        raise AssertionError("Not found '%s' key to compare values in dict"
                             % actual_key)


ut = PysonarTest()


    
def as_unit(fn):
    @functools.wraps(fn)
    def wrapper():
        return fn(PysonarTest())
    return wrapper


def find_in_history(id_, ps):
    for ast_node, value in ps.history.iteritems():
        if (isinstance(ast_node, ast.Name)
            and ast_node.id == id_):
            return value

def first_in_history(id_, ps):
    values = find_in_history(id_, ps)
    if values:
        return values[0]
