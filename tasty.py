
from unittest.case import TestCase
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
        r[_get_value(p.fst)[0]] = _get_value(p.snd)[0]
    return r


class PysonarTest(TestCase):

    def runTest(self):
        pass
    
    def _assert(self, expected, actual, msg="Different values"):
        if expected != actual:
            raise AssertionError("%s: %s != %s" % (msg, expected, actual))
    
    def _assertType(self, expected_type, actual_value):
        if not isinstance(actual_value, expected_type):
            raise AssertionError("Expected type %s but got %s" %
                                 (expected_type, actual_value))

    
    def assertNum(self, expected, actual):
        self._assertType(ast.Num, actual)
        self._assert(expected, actual.n)
    
    def assertFlattenedList(self, expected, actual):
        '@types: list, ListType'
        actual = ps.ListType(flatten(actual.elts))
        self.assertList(expected, actual)

    def assertList(self, expected, actual):
        '@types: dict, pysonar.ListType'
        self._assertType(ps.ListType, actual)
        actual = actual.elts
        self._assert(len(expected), lists.length(actual), "Size mismatch")
        for i, actual_value in enumerate(actual):
            self._assert(expected[i], _get_value(actual_value),
                         "Different values at index: %s" % i)

    def assertDict(self, expected, actual):
        '@types: dict, pysonar.DictType'
        self._assertType(ps.DictType, actual)
        actual = actual.dict
        self._assert(len(expected), lists.length(actual), "Size mismatch")
        for item_pair in actual:
            keys, values = item_pair.fst, item_pair.snd
            actual_key = _get_value(keys[0])
            actual_value = _get_value(values[0])
            self._assert(expected.get(actual_key), actual_value,
                         "Different values for the same key: %s" % actual_key)
            
    def assertSubDict(self, expected, actual):
        '@types: dict, pysonar.DictType'
        self._assertType(ps.DictType, actual)
        actual = actual.dict
        for item_pair in actual:
            keys, values = item_pair.fst, item_pair.snd
            actual_key = _get_value(keys[0])
            if expected.has_key(actual_key):
                actual_value = _get_value(values[0])
                self._assert(expected.get(actual_key), actual_value,
                             "Different values for the same key: %s" % actual_key)
                
    def assertDictValueAsDict(self, expected, actual_dict, actual_key):
        self._assertType(ps.DictType, actual_dict)
        actual = actual_dict.dict
        for item_pair in actual:
            keys, values = item_pair.fst, item_pair.snd
            if actual_key == _get_value(keys[0]):
                actual_value = values[0]
                self._assertType(ps.DictType, actual_value)
                self._assert(expected, get_dict_with_flattened_values(actual_value),
                             "Different values for the same key: %s" % actual_key)
                return
        raise AssertionError("Not found '%s' key to compare values in dict"
                             % actual_key)
    
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