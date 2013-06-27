#!/usr/bin/python
import pysonar
import sys
import os

if __name__ == '__main__':
    pysonar.addToPythonPath(os.path.dirname(sys.argv[1]))
    pysonar.checkFile(sys.argv[1])
    for class_name, val in pysonar.MYDICT.items():
        print class_name
        for a in val:
            print a
