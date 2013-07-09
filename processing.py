#!/usr/bin/python
import pysonar
import sys
import os
import ast
from collections import defaultdict

# lookup arg in env if it is Name
def convertName(arg, env):
    if pysonar.IS(arg, ast.Name):
        return pysonar.lookup(arg.id, env)
    return arg


if __name__ == '__main__':
    pysonar.addToPythonPath(os.path.dirname(sys.argv[1]))
    pysonar.checkFile(sys.argv[1])
    constructor_params = defaultdict(set)
    for class_name, val in pysonar.getMethodInvocationInfo().items():
        print class_name
        for constrargs, args, env in val:
            print constrargs, args
            if constrargs:
                for first_constructor_arg in constrargs[0]:
                    constructor_params[class_name].add(first_constructor_arg)
#            print '\t', constrargs, map(lambda arg: convertName(arg, env), args)
    print constructor_params
