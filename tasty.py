
from unittest.case import TestCase
import ast
import functools

class _DummyTest(TestCase):

    def runTest(self):
        pass
    
def as_unit(fn):
    @functools.wraps(fn)
    def wrapper():
        return fn(_DummyTest())
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