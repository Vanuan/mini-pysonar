#!/usr/bin/python
import pysonar
import sys
import os
import ast

# lookup arg in env if it is Name
def convertName(arg, env):
    if pysonar.IS(arg, ast.Name):
        return pysonar.lookup(arg.id, env)
    return arg


if __name__ == '__main__':
    pysonar.addToPythonPath(os.path.dirname(sys.argv[1]))
    pysonar.checkFile(sys.argv[1])
    for class_name, val in pysonar.getMethodInvocationInfo().items():
        print class_name
        for constrargs, args, env in val:
            print constrargs, args
#            print '\t', constrargs, map(lambda arg: convertName(arg, env), args)
