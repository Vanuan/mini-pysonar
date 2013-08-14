# pysonar.py - a Python version of PySonar static analyzer for Python
# Copyright (C) 2011 Yin Wang (yinwang0@gmail.com)
# coding=utf-8
import sys
import re
import ast
from ast import parse, ClassDef, FunctionDef, Attribute, Name, List, Tuple,\
    If, While, For, Assign, AugAssign, Expr, Return, Import, ImportFrom,\
    Continue, TryExcept, TryFinally, ExceptHandler, Raise, Assert, Module,\
    Num, Str, Call, Lambda, Break, Global, With, Print, Pass, AST, BinOp,\
    Compare, Mult, Add
from lists import nil, ext, first, rest, assq, reverse, maplist,\
    SimplePair, append
import lists

from collections import defaultdict
import os
import logging
from functools import partial
import types as types1
import copy

logging.basicConfig(filename="_pysonar.log", level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)


def _log(fn, *args):
    #fn(' '.join(map(str, args)))
    pass

debug = partial(_log, logger.debug)
warn = partial(_log, logger.warn)
error = partial(_log, logger.error)


####################################################################
## global parameters
####################################################################
IS = isinstance

# dict[str, list]
# class/type name       -> list[tuple[
#                               list[list[initializator arguments]],
#                               list[list[call arguments]],
#                               ENV
#                       ]]
MYDICT = defaultdict(list)
PYTHONPATH = []
FILES_TO_SKIP = set()
imported_modules = {}
module_objects = {}


####################################################################
## utilities
####################################################################
def iter_fields(node):
    """Iterate over all existing fields, excluding 'ctx'."""
    for field in node._fields:
        try:
            if field != 'ctx':
                yield field, getattr(node, field)
        except AttributeError:
            pass

# for debugging


def dp(s):
    return map(dump, parse(s).body)


def pf(file_):
    import cProfile
    cProfile.run("sonar(" + file_ + ")", sort="cumulative")


####################################################################
## test on AST nodes
####################################################################
def isAtom(x):
    return type(x) in [int, str, bool, float]


def isDef(node):
    return IS(node, FunctionDef) or IS(node, ClassDef)


##################################################################
# per-node information store
##################################################################
history = {}


def putInfo(exp, item):
    if exp in history:
        seen = history[exp]
    else:
        seen = []
    history[exp] = union([seen, item])


def getInfo(exp):
    return history[exp]


##################################################################
# types used by pysonar
##################################################################
class Type:
    pass


nUnknown = 0


class UnknownType(Type):
    def __init__(self, obj):
        assert obj is not None
        self.obj = obj

        global nUnknown
        nUnknown += 1

    def __repr__(self):
        return "Unknown(%r)" % self.obj

    def __hash__(self):
        return hash(self.obj.lineno)

    def __eq__(self, other):
        if IS(other, UnknownType):
            return self.obj.lineno == other.obj.lineno
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class PrimType(Type):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return str(self.name)

    def __eq__(self, other):
        if IS(other, PrimType):
            return self.name == other.name
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
    def __hash__(self):
        return hash(self.name)


class ClassType(Type):
    def __init__(self, name, bases, body, env, ast_def_class):
        '@types: str, list[ast.AST], list[ast.AST], LinkedList'
        assert IS(name, str)
        self.name = name
        self.env = env
        self.attrs = {}
        self.ast = ast_def_class
        self.bases = bases
        if name not in ('module', 'dict', 'list'):
            assert body  # empty body is not allowed for class
        self.body = body

    def infer_body(self, stk):
        if self.name != 'module':
            self.__saveClassAttrs(self.body, stk)
        else:
            for pair in self.env:
                self.attrs[pair.fst] = pair.snd

    def infer_bases(self, stk):
        debug('infer bases of %s: %s' % (self, self.bases))
        baseClasses = []
        for base in self.bases:
            if IS(base, Name) and base.id == 'object':
                continue
            if IS(base, (Call, Attribute)):
                inferredBaseClasses = infer(base, self.env, stk)
            else:
                inferredBaseClasses = lookup(base.id, self.env)
                if not inferredBaseClasses:
                    inferredBaseClasses = ()
            baseClasses.extend(inferredBaseClasses)

        for baseClass in baseClasses:
            if IS(baseClass, ClassType):
                for key, val in baseClass.attrs.iteritems():
                    self.attrs[key] = val
            else:
                logger.error('Can\'t infer base of %s: %s %s'
                             % (self.name, baseClass, base))

    def getattr(self, name):
        return self.attrs.get(name, ())
    def hasattr(self, name):
        return name in self.attrs

    def __saveClassAttrs(self, body, stk):
        # infer body
        local_env = close(body, nil)  # {Name.id -> (Closure | ClassType)}
        mixed_env = close(body, self.env)
        _, mixed_env = inferSeq(body, mixed_env, stk)  # Closure's env will be updated,
        for pair in local_env:
            # Closure's env will be updated, when invoking MethodType
            self.attrs[pair.fst] = lookup(pair.fst, mixed_env)

    def __repr__(self):
        return "ClassType:" + str(self.ast)

    def __eq__(self, other):
        if IS(other, ClassType):
            return self.name == other.name
        else:
            return False

    def __hash__(self):
        return hash(self.ast)

    def __ne__(self, other):
        return not self.__eq__(other)


class ObjType(Type):
    def __init__(self, classtype, ctorargs, env, ast):
        '@types: ClassType, list[Type], LinkedList, ast'
        self.classtype = classtype
        self.attrs = {}
        # copy class attributes over to instance
        for name, attr in self.classtype.attrs.iteritems():
            closures = filter(lambda attr: IS(attr, Closure), attr)
            non_closures = filter(lambda attr: not IS(attr, Closure), attr)
            if closures:
                # if it is a closure, create an instance method reference
                self.attrs[name] = (MethodType(closures, self),)
            if non_closures:
                self.attrs[name] = non_closures
        debug("object %s: %s" % (self.classtype.name, self.attrs))
        self.ctorargs = ctorargs
        self.ast = ast

    def getattr(self, name):
        return self.attrs.get(name, ())

    def hasattr(self, name):
        return name in self.attrs

    def __repr__(self):
        return ("'" + str(self.classtype.name) + "' instance"
                # + ", ctor:" + str(self.ctorargs)
                # + ", attrs:" + str(self.attrs)
                )

    def __eq__(self, other):
        if IS(other, ObjType):
            return ((self.classtype == other.classtype) and
                    self.attrs.keys() == other.attrs.keys())
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.ast)


class FuncType(Type):
    def __init__(self, fromtype, totype):
        self.fromtype = fromtype
        self.totype = totype

    def __repr__(self):
        return str(self.fromtype) + " -> " + str(self.totype)

    def __eq__(self, other):
        return (IS(other, FuncType)
                and (self.fromtype == other.fromtype)
                and self.totype == other.totype)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        # print self.fromtype, self.totype
        hash1 = hash(tuple(self.fromtype))
        hash2 = hash(tuple(self.totype))
        return hash1 + hash2 


class MethodType(Type):
    '''
    This is an analog to Name, just for object attributes

    Reference on object attribute value, so binds object with this value while
    name is determined in the context (or environment)
    '''
    def __init__(self, closures, o):
        '''@types: list[Closure], ObjType|DictType
        '''
        # self.env = closure.env
        assert IS(closures, (list, tuple))
        self.clo = closures
        self.obj = o

    def __repr__(self):
        clo_repr = ','.join(map(str, self.clo))
        return '(method %s of %s)' % (clo_repr, self.obj.classtype.name)

    def __eq__(self, other):
        if IS(other, FuncType):
            return (self.clo == other.clo)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(tuple(self.clo)) + hash(self.obj)


class Closure(Type):
    def __init__(self, func, env):
        '@types: ast.FunctionDef, LinkedList'
        self.func = func
        self.env = env
        self.defaults = []

    def __repr__(self):
        return str(self.func)


class TupleType(Type):
    def __init__(self, elts):
        self.elts = elts

    def __repr__(self):
        return "tup:" + repr(self.elts)

    def __eq__(self, other):
        if IS(other, TupleType):
            if len(self.elts) != len(other.elts):
                return False
            else:
                for i in xrange(len(self.elts)):
                    if self.elts[i] != other.elts[i]:
                        return False
                return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


class ListType(Type):
    '''
    To lower performance impact, let's store only unique values in the list
    '''
    def __init__(self, elts):
        '@types: tuple'
        self.elts = tuple(elts)
        self.attrs = {'append': [MethodType([self.append], self)],
                      'extend': [MethodType([self.extend], self)]
                     }
        self.classtype = ClassType('list', [], [], nil, None)

    def __repr__(self):
        return "list:" + repr(self.elts)

    def __eq__(self, other):
        return (IS(other, ListType)
                and self.elts == other.elts)

    def __hash__(self):
        return hash(self.elts)

    def __iter__(self):
        return iter(self.elts)

    def __ne__(self, other):
        return not self.__eq__(other)

    def getattr(self, name):
        return self.attrs.get(name, ())

    def hasattr(self, name):
        return name in self.attrs

    def append(self, others):
        for other in others:
            self.elts += (other,)

    def extend(self, others):
        for other in others:
            if IS(other, Bind):
                self.elts += other.typ.elts
            else:
                error("Extend called with unknown argument type", other)


def flatten(list_of_lists):
    # TODO: handle __iter__ and next()
    flattened = []
    for sublist in list_of_lists:
        if not isinstance(sublist, TypeError):
            try:
                flattened.extend([i for i in sublist])
            except TypeError, _:
                flattened.append(sublist)
        else:
            flattened.append(sublist)
    return flattened


class DictType(Type):

    def __init__(self, dict_):
        '@types: LinkedList'
        self.dict = dict_
        self.attrs = {'keys': [MethodType([self.get_keys], self)],
                      'iterkeys': [MethodType([self.get_keys], self)],
                      'values': [MethodType([self.get_values], self)],
                      'itervalues': [MethodType([self.get_values], self)],
                      'items': [MethodType([self.get_items], self)],
                      'iteritems': [MethodType([self.get_items], self)],
                      'get': [MethodType([self.get_key], self)]}
        self.classtype = ClassType('dict', [], [], nil, None)
        self.iter_operations = (self.get_keys, self.get_values, self.get_items)


    def getattr(self, name):
        return self.attrs.get(name, ())

    def hasattr(self, name):
        return name in self.attrs

    # Since we are not infering body's,
    # these functions should always return a list:

    #@staticmethod
    def get_key(self, key, default=None):
        '@types: LinkedList, ? -> list'
        # potentially, any value can be returned
        value = flatten([key_value_pair.snd for key_value_pair in self.dict])
        if default:
            value.extend(default)
        return tuple(value)

    def set_key(self, key, value):
        self.dict = mergeEnv(ext(key, value, nil), self.dict, True)
        debug('updating dict with', value, self)

    #@staticmethod
    def get_keys(self):
        '@types: LinkedList -> list'
        return tuple([key_value_pair.fst for key_value_pair in self.dict])

    #@staticmethod
    def get_values(self):
        '@types: LinkedList -> list'
        return tuple([key_value_pair.snd for key_value_pair in self.dict])

    #@staticmethod
    def get_items(self):
        '@types: LinkedList -> list'
        return tuple([TupleType([[pair.fst], pair.snd]) for pair in self.dict])

    def __repr__(self):
        return "dict:" + unicode(self.dict)

    # any hashable value can be used as keys
    # any object can be used as values
    # so we can know almost nothing about the dictionaries
    def __eq__(self, other):
        return IS(other, DictType)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        try:
            return hash(self.dict.fst)
        except:
            return hash(self.dict)

class UnionType(Type):
    def __init__(self, elts):
        self.elts = elts

    def __repr__(self):
        return "U:" + unicode(self.elts)


# singleton primtive types
contType = PrimType('cont')             # continuation type
bottomType = PrimType('_|_')            # non-terminating recursion


# need to rewrite this when we have recursive types
def typeEqual(t1, t2):
    if IS(t1, list) and IS(t2, list):
        for bd1 in t1:
            if bd1 not in t2:
                return False
        return True
    else:
        return t1 == t2


def subtypeBindings(rec1, rec2):
    def find(a, rec2):
        for b in rec2:
            if (first(a) == first(b)) and typeEqual(rest(a), rest(b)):
                return True
        return False
    for a in rec1:
        if not find(a, rec2):
            return False
    return True


def union(ts):
    u = set()
    listTypeElts = set()
    list_is_present = False
    for t in ts:
        if IS(t, (list, tuple)):                 # already a union (list)
            for b in t:
                list_is_present = list_is_present or merge(b, u, listTypeElts)
        else:
            list_is_present = list_is_present or merge(t, u, listTypeElts)
    if list_is_present:
        u.add(ListType(tuple(listTypeElts)))
    return tuple(u)


def merge(element, typesset, listtypeset):
    list_is_present = False
    if element:
        if IS(element, ListType):
            list_is_present = True
            listtypeset.update(element.elts)
        else:
            typesset.add(element)
    return list_is_present


def resolve_attribute(attr_list):
    resolved = []
    for attr in attr_list:
        if IS(attr, MethodType):
            resolved.extend(resolve_attribute(attr.clo))
        else:
            resolved.append(attr)
    return tuple(resolved)


####################################################################
## type inferencer
####################################################################
class Bind:
    def __init__(self, typ, loc):
        self.typ = typ
        self.loc = loc

    def __hash__(self):
        return hash(self.loc)

    def __repr__(self):
        return "(" + repr(self.typ) + " <~~ " + repr(self.loc) + ")"

    def __iter__(self):
        return self.typ.elts.__iter__()#BindIterator(self)

    def __eq__(self, other):
        return (IS(other, Bind) and
                self.typ == other.typ and
                self.loc == other.loc)

    def getattr(self, name):
        return self.typ.getattr(name)

    def hasattr(self, name):
        return self.typ.hasattr(name)


class BindIterator:
    def __init__(self, p):
        self.p = p
        self.cur = 0

    def next(self):
        if self.cur == 2:
            raise StopIteration
        elif self.cur == 0:
            self.cur += 1
            return self.p.typ
        else:
            self.cur += 1
            return self.p.loc


def typeOnly(bs):
    return union(bs)


# test whether a type is in a union
def inUnion(t, u):
    for t2 in u:
        if t == t2:
            return True
    return False


def removeType(t, u):
    return [x for x in u if x != t]


# combine two environments, make unions when necessary
# if append=False, only assocs appear in both envs are preserved
# use a variable bound in only one branch will cause type error
def mergeEnv(env1, env2, append=False):
    ret = nil
    for p1 in env1:
        p2 = assq(first(p1), env2)
        if p2 != None:
            ret = ext(first(p1), union([rest(p1), rest(p2)]), ret)
        else:
            if append:
                ret = ext(first(p1), union([rest(p1)]), ret)
    return reverse(ret)


# compare both str's and Name's for equivalence, because
# keywords are str's (bad design of the ast)
def getId(x):
    if IS(x, Name):
        return x.id
    else:
        return x


def getName(x, lineno):
    return Name(id=x, lineno=lineno)


def bind(target, infered_value, env, stk):
    if IS(target, Name) or IS(target, str):
        u = infered_value
        putInfo(target, u)
        return ext(getId(target), u, env)
    elif IS(target, Attribute):
        attribute_value = target.value
        infered_targets = infer(attribute_value, env, nil)
        for obj in infered_targets:
            if IS(obj, (ClassType, ObjType)):
                obj.attrs[target.attr] = infered_value
            else:
                error("Syntax error: wrong target type in assignment: ",
                      obj, type(obj))
        return env

    elif IS(target, Tuple) or IS(target, List):
        infered_values = infered_value
        target_to_value = defaultdict(list)
        for infered_value in infered_values:
            if IS(infered_value, TupleType) or IS(infered_value, List):
                debug('infered key, value:', infered_value)
                if len(target.elts) == len(infered_value.elts):
                    for i in xrange(len(infered_value.elts)):
                        target_to_value[target.elts[i]].extend(infered_value.elts[i])
                elif len(target.elts) < len(infered_value.elts):
                    putInfo(target, ValueError('too many values to unpack'))
                else:
                    putInfo(target, ValueError('too few values to unpack'))
            else:
                putInfo(target, TypeError('non-iterable object'))
        for key, value in target_to_value.iteritems():
            debug('binding %s to %s:' % (key, value))
            env = bind(key, value, env, stk)
        return env

    elif IS(target, ast.Subscript):
        t = infer(target.value, env, stk)
        for tt in t:
            #if IS(tt, Bind):
            #    if IS(exp.slice, ast.Index):
            #        types.extend(tt.typ.elts)
            #    else:
            #        types.extend(t)
            if IS(tt, DictType) and IS(target.slice, ast.Index):
                subscripts = infer(target.slice.value, env, stk)
                for subscript in subscripts:
                    tt.set_key(subscript, infered_value)
            else:
                error("Syntax error: Subscript type is not supported in assignment: ", target)
        return env
    else:
        putInfo(target, SyntaxError("not assignable"))
        return env


def onStack(call, args, stk):
    for p1 in stk:
        call2 = first(p1)
        args2 = rest(p1)
        if call == call2 and subtypeBindings(args, args2):
            return True
    return False


def saveMethodInvocationInfo(call, method, env, stk):
    '''
    @types: ast.Call, MethodType, LinkedList, LinkedList -> None
    '''
    if call.args:
        ctorargs = [a for a in method.obj.ctorargs]
        method_names = [closure.func.name for closure in method.clo]
        # here we do redundant inference of arguments,
        # but there seems to be no other simple way
        # to save both class name and infered arguments
        callargs = [resolve_attribute(infer(arg, env, stk)) for arg in call.args]
        # TODO save keywords
        MYDICT[method.obj.classtype.name].append((ctorargs, callargs, env, method_names))


def getMethodInvocationInfo():
    return MYDICT


def is_callable(clo):
    return (IS(clo, (Closure, ClassType, MethodType, types1.MethodType))) or\
           (IS(clo, ObjType) and clo.hasattr('__call__'))


# invoke one closure
def invoke1(call, clo, env, stk):
    '''@types: ast.Call, Callable, LinkedList, LinkedList -> ast.AST or Type
    '''
    if (clo == bottomType):
        return [bottomType]
    # Even if operator is not a callable, resolve the
    # arguments for partial information.
    if not is_callable(clo):
        # infer arguments even if it is not callable
        # probably causes infinite recursion
        debug('Object is not callable, infering arguments', call.args)
        for a in call.args:
            infer(a, env, stk)
        for k in call.keywords:
            infer(k.value, env, stk)
        err = '?'#TypeError('calling non-callable')#, clo.func.name)
        putInfo(call, err)
        return [err]
    if IS(clo, ClassType):
        debug('creating instance of', clo)
        ctorargs = [infer(arg, env, stk) for arg in call.args]
        new_obj = ObjType(clo, ctorargs, clo.env, call)
        init_closures = new_obj.getattr('__init__')
        if len(init_closures):
            invoke1(call, init_closures[0], env, stk)
        return [new_obj]
    elif IS(clo, MethodType):
        attr = clo
        if IS(attr.obj, ObjType):
            # add self to function call args
            actualParams = list(call.args)
            classtype = attr.obj.classtype
            saveMethodInvocationInfo(call, attr, env, stk)
            # TODO: @staticmethod, @classmethod
            if classtype.name != 'module':
                # we don't really care about this name,
                # we just don't want to collide
                # with names, available in method
                # TODO: generate a special name,
                #       that would represent a temporary object
                self_arg = get_self_arg_name(attr.clo[0].func)
                env_with_self = ext(self_arg.id, [attr.obj], env)
                env = env_with_self
                # add self to params
                actualParams.insert(0, self_arg)
            types = []
            for closure in attr.clo:
                if IS(closure, Closure):
                    if closure.func.filename not in FILES_TO_SKIP:
                        debug('invoking method', closure.func.name,
                              'with args', call.args)
                        types.extend(invokeClosure(call, actualParams, closure,
                                                   env, stk))
                elif IS(closure, ClassType):
                    types.extend(invoke1(call, closure, env, stk))
                else:
                    types.append(TypeError("Callable type %s is not supported"
                                           % closure))
            return tuple(types)
        elif IS(attr.obj, (DictType, ListType)):
            types = []
            for closure in attr.clo:
                if IS(closure, types1.MethodType):
                    # print 'invoking method of dict', closure
                    # we take the first version of infered arguments
                    # but ideally all must be processed
                    infered_args = [infer(arg, env, stk) for arg in call.args]
                    method_returned = closure(*infered_args)
                    if method_returned:
                        types.extend(method_returned)
            return types
        else:
            err = TypeError('MethodType object is not supported for the invoke',
                            attr)
            putInfo(call, err)
            return (err,)
    elif IS(clo, ObjType):
        types = []
        call_closures = clo.getattr('__call__')
        for call_closure in call_closures:
            types.extend(invoke1(call, call_closure, env, stk))
        return tuple(types)
    else:  # Closure
        if clo.func.filename not in FILES_TO_SKIP:
            return invokeClosure(call, call.args, clo, env, stk)
        else:
            return (TypeError('Skipped', clo.func,
                              'in', clo.func.filename))


def get_self_arg_name(fn_def):
    ''' Expecting to get ast.Name with id, for instance, self
    @types: ast.FunctionDef -> ast.Name
    '''
    if not fn_def.args.args:
        raise ValueError("Bound method '%s' should have at least one parameter" % str(fn_def.name))
    arg = fn_def.args.args[0]
    if IS(arg, ast.Name):
        self_arg = copy.copy(arg)
        self_arg.id = '__pysonar_self__'
        return self_arg
    msg = "Method definition %s doesn't have self as first argument"
    raise ValueError(msg % fn_def.name)


def invokeClosure(call, actualParams, clo, env, stk):
    '''
    @types: ast.Call, list[ast.AST], Closure, LinkedList, LinkedList -> list[Type]
    '''
    debug('invoking closure', clo.func, 'with args', actualParams)

    debug('closure body:', clo.func.body)

    func = clo.func
    fenv = clo.env
    pos = nil
    kwarg = nil

    # bind positionals first
    poslen = min(len(func.args.args), len(actualParams))
    for i in xrange(poslen):
        t = infer(actualParams[i], env, stk)
        pos = bind(func.args.args[i], t, pos, stk)

    # put extra positionals into vararg if provided
    # report error and go on otherwise
    if len(actualParams) > len(func.args.args):
        if func.args.vararg == None:
            err = TypeError('excess arguments to function')
            putInfo(call, err)
            return [err]
        else:
            ts = []
            for i in xrange(len(func.args.args), len(actualParams)):
                t = infer(actualParams[i], env, stk)
                ts = tuple(ts) + tuple(t)
            ts = [Bind(ListType(ts), func.args.vararg)]
            pos = bind(func.args.vararg, ts, pos, stk)

    # put starargs to vararg or args
    if call.starargs:
        tt = infer(call.starargs, env, stk)

        ts = []
        for t in tt:
            if IS(t, Bind):
                ts.append(t)
        if func.args.vararg:
            pos = bind(func.args.vararg, ts, pos, stk)
        else:
            for t in ts:
                for i in range(len(func.args.args)):
                    pos = bind(func.args.args[i], t.typ.elts, pos, stk)

    # bind keywords, collect kwarg
    ids = map(getId, func.args.args)
    for k in call.keywords:
        ts = infer(k.value, env, stk)
        tloc1 = lookup(k.arg, pos)
        if tloc1 != None:
            putInfo(call, TypeError('multiple values for keyword argument',
                                     k.arg, tloc1))
        elif k.arg not in ids:
            kwarg = bind(k.arg, ts, kwarg, stk)
        else:
            pos = bind(k.arg, ts, pos, stk)

    # put extras in kwarg or report them
    # bind call.keywords to func.args.kwarg
    if kwarg != nil:
        if func.args.kwarg != None:
            pos = bind(func.args.kwarg, [DictType(reverse(kwarg))], pos, stk)
        else:
            putInfo(call, TypeError("unexpected keyword arguements", kwarg))
    elif func.args.kwarg != None:
        pos = bind(func.args.kwarg, [DictType(nil)], pos, stk)

    # bind defaults, avoid overwriting bound vars
    # types for defaults are already inferred when the function was defined
    i = len(func.args.args) - len(func.args.defaults)
    _ = len(func.args.args)
    for j in xrange(len(clo.defaults)):
        tloc = lookup(getId(func.args.args[i]), pos)
        if tloc == None:
            pos = bind(func.args.args[i], clo.defaults[j], pos, stk)
            i += 1

    # finish building the input type
    fromtype = maplist(lambda p: SimplePair(first(p), typeOnly(rest(p))), pos)

    # check whether the same call site is on stack with same input types
    # if so, we are back to a loop, terminate
    if onStack(call, fromtype, stk):
        return [bottomType]

    # push the call site onto the stack and analyze the function body
    stk = ext(call, fromtype, stk)
    fenv = append(pos, fenv)
    to = infer(func.body, fenv, stk)

    # record the function type
    putInfo(func, FuncType(reverse(fromtype), to))
    return to


# invoke a union of closures. call invoke1 on each of them and collect
# their return types into a union
def invoke(call, env, stk):
    clos = infer(call.func, env, stk)
    totypes = []
    for clo in clos:
        t = invoke1(call, clo, env, stk)
        totypes.extend(t)
    return tuple(totypes)


# pre-bind names to functions in sequences
def close(code_block, env):
    '''@types: list[ast.AST], LinkedList -> LinkedList'''
    for e in code_block:
        if IS(e, FunctionDef):
            c = Closure(e, nil)
        elif IS(e, ClassDef):
            # env is needed to infer bases
            # (maybe it's better to move base inference out of constructor)
            c = ClassType(e.name, e.bases, e.body, env, e)
        elif IS(e, (Import)):
            for module_name in e.names:
                name_to_import = module_name.name
                module_obj = getModuleObject(name_to_import)
                name_import_as = module_name.asname or module_name.name
                env = bind(getName(name_import_as, e.lineno), [module_obj], env, nil)
        # TODO: here we also need ImportFrom and Assign
        # Assign is complicated
        elif IS(e, Assign):
            for x in e.targets:
                # here we prepare a local scope for class args inference
                # (see __saveClassAttrs method)
                env = bind(x, (), env, nil)
        if IS(e, (FunctionDef, ClassDef)):
            env = ext(e.name, [c], env)
    return env


def getModuleObject(name_to_import):
    if name_to_import not in module_objects:
        module, module_env = get_module_symbols(name_to_import)
        module_class = ClassType('module', [], module.body, module_env, None)
        module_class.infer_body(nil)
        module_obj = ObjType(module_class, [], nil, None)
        module_objects[name_to_import] = module_obj
    else:
        module_obj = module_objects[name_to_import]
    return module_obj


def isTerminating(t):
    return not inUnion(contType, t)


def finalize(t):
    return removeType(contType, t)


# infer a sequence of statements
def inferSeq(exp, env, stk):
    debug('Infering sequence', exp)

    if exp == []:                       # reached end without return
        return ([contType], env)

    e = exp[0]
    if IS(e, If):
        _ = infer(e.test, env, stk)
        (t1, env1) = inferSeq(e.body, close(e.body, env), stk)
        (t2, env2) = inferSeq(e.orelse, close(e.orelse, env), stk)

        if isTerminating(t1) and isTerminating(t2):          # both terminates
            for e2 in exp[1:]:
                putInfo(e2, TypeError('unreachable code'))
            return (union([t1, t2]), env)

        elif isTerminating(t1) and not isTerminating(t2):    # t1 terminates
            (t3, env3) = inferSeq(exp[1:], env2, stk)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

        elif not isTerminating(t1) and isTerminating(t2):    # t2 terminates
            (t3, env3) = inferSeq(exp[1:], env1, stk)
            t1 = finalize(t1)
            return (union([t1, t2, t3]), env3)
        else:                                            # both non-terminating
            (t3, env3) = inferSeq(exp[1:], mergeEnv(env1, env2), stk)
            t1 = finalize(t1)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

    elif IS(e, While):
        # todo evaluate test
        (t1, env1) = inferSeq(e.body, close(e.body, env), stk)
        (t2, env2) = inferSeq(e.orelse, close(e.orelse, env), stk)

        if isTerminating(t1) and isTerminating(t2):          # both terminates
            for e2 in exp[1:]:
                putInfo(e2, TypeError('unreachable code'))
            return (union([t1, t2]), env)

        elif isTerminating(t1) and not isTerminating(t2):   # t1 terminates
            (t3, env3) = inferSeq(exp[1:], env2, stk)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

        elif not isTerminating(t1) and isTerminating(t2):   # t2 terminates
            (t3, env3) = inferSeq(exp[1:], env1, stk)
            t1 = finalize(t1)
            return (union([t1, t2, t3]), env3)
        else:                                            # both non-terminating
            (t3, env3) = inferSeq(exp[1:], mergeEnv(env1, env2), stk)
            t1 = finalize(t1)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

    elif IS(e, For):
        values = infer(e.iter, env, stk)
        value = flatten(values)
        env = bind(e.target, value, env, stk)
        (t1, env1) = inferSeq(e.body, close(e.body, env), stk)
        (t2, env2) = inferSeq(e.orelse, close(e.orelse, env), stk)

        if isTerminating(t1) and isTerminating(t2):           # both terminates
            for e2 in exp[1:]:
                putInfo(e2, TypeError('unreachable code'))
            return (union([t1, t2]), env)

        elif isTerminating(t1) and not isTerminating(t2):    # t1 terminates
            (t3, env3) = inferSeq(exp[1:], env2, stk)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

        elif not isTerminating(t1) and isTerminating(t2):    # t2 terminates
            (t3, env3) = inferSeq(exp[1:], env1, stk)
            t1 = finalize(t1)
            return (union([t1, t2, t3]), env3)
        else:                                           # both non-terminating
            (t3, env3) = inferSeq(exp[1:], mergeEnv(env1, env2), stk)
            t1 = finalize(t1)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

    elif IS(e, Assign):
        t = infer(e.value, env, stk)
        for x in e.targets:
            env = bind(x, t, env, stk)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, AugAssign):
        t = infer(e.value, env, stk)
        env = bind(e.target, t, env, stk)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, FunctionDef):
        cs = lookup(e.name, env)
        if not cs:
            debug('Function %s not found in scope %s' % (e.name, env))
        for c in cs:
            c.env = env              # create circular env to support recursion
        for d in e.args.defaults:    # infer types for default arguments
            dt = infer(d, env, stk)
            c.defaults.append(dt)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, Return):
        if e.value is None:
            t1 = (PrimType(None),)
        else:
            t1 = infer(e.value, env, stk)
        (t2, env2) = inferSeq(exp[1:], env, stk)
        for e2 in exp[1:]:
            putInfo(e2, TypeError('unreachable code'))
        return (t1, env)

    elif IS(e, Expr):
        t1 = infer(e.value, env, stk)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, ImportFrom):
        _, module_symbols = get_module_symbols(e.module)
        for module_name in e.names:
            name_to_import = module_name.name
            name_import_as = module_name.asname or name_to_import
            module_symbol = lookup(name_to_import, module_symbols)
            if module_symbol:
                env = bind(getName(name_import_as, e.lineno), module_symbol, env, stk)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, Import):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, ClassDef):
        cs = lookup(e.name, env)
        if not cs:
            error('Class def %s not found in scope %s' % (e.name, env))
        for c in cs:
            c.env = env
            c.infer_bases(stk)
            c.infer_body(stk)  # infer the body only after env is changed

        (t2, env2) = inferSeq(exp[1:], env, stk)
        return (t2, env2)

    elif IS(e, Break):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, Continue):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, TryExcept):
        (t1, env1) = inferSeq(e.body, close(e.body, env), stk)
        (t2, env2) = inferSeq(e.orelse, close(e.orelse, env), stk)
        (_, _) = inferSeq(e.handlers, close(e.handlers, env), stk)

        if isTerminating(t1) and isTerminating(t2):           # both terminates
            for e2 in exp[1:]:
                putInfo(e2, TypeError('unreachable code'))
            return (union([t1, t2]), env)

        elif isTerminating(t1) and not isTerminating(t2):     # t1 terminates
            (t3, env3) = inferSeq(exp[1:], env2, stk)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

        elif not isTerminating(t1) and isTerminating(t2):    # t2 terminates
            (t3, env3) = inferSeq(exp[1:], env1, stk)
            t1 = finalize(t1)
            return (union([t1, t2, t3]), env3)
        else:                                           # both non-terminating
            (t3, env3) = inferSeq(exp[1:], mergeEnv(env1, env2), stk)
            t1 = finalize(t1)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

    elif IS(e, TryFinally):
        (t1, env1) = inferSeq(e.body, close(e.body, env), stk)
        (t2, env2) = inferSeq(e.finalbody, close(e.finalbody, env), stk)

        if isTerminating(t1) and isTerminating(t2):        # both terminates
            for e2 in exp[1:]:
                putInfo(e2, TypeError('unreachable code'))
            return (union([t1, t2]), env)

        elif isTerminating(t1) and not isTerminating(t2):     # t1 terminates
            (t3, env3) = inferSeq(exp[1:], env2, stk)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

        elif not isTerminating(t1) and isTerminating(t2):    # t2 terminates
            (t3, env3) = inferSeq(exp[1:], env1, stk)
            t1 = finalize(t1)
            return (union([t1, t2, t3]), env3)
        else:                                            # both non-terminating
            (t3, env3) = inferSeq(exp[1:], mergeEnv(env1, env2), stk)
            t1 = finalize(t1)
            t2 = finalize(t2)
            return (union([t1, t2, t3]), env3)

    elif IS(e, ExceptHandler):
        (t1, env1) = inferSeq(e.body, close(e.body, env), stk)
        (t3, env3) = inferSeq(exp[1:], env1, stk)
        return (union([t1, t3]), env3)

    elif IS(e, Raise):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, Pass):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, Print):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, With):
        # TODO infer e.context_expr,
        # call __enter__ from e.context_expr
        # bind e.optional_vars to the result of __enter__
        # call __exit__
        (t1, env1) = inferSeq(e.body, close(e.body, env), stk)
        (t2, env2) = inferSeq(exp[1:], env1, stk)
        return (union([t1, t2]), env2)

    elif IS(e, Assert):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, Global):
        # TODO this should affect bind behaviour when assigning
        # We don't have a way to change env for now,
        # we can only append
        # see tests/assign.py
        return inferSeq(exp[1:], env, stk)
    elif IS(e, ast.Delete):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, ast.Exec):
        return inferSeq(exp[1:], env, stk)

    else:
        raise TypeError('recognized node in effect context', e)


def get_attribute(exp, inferred_type, attribute_name):
    attribs = []
    for obj in inferred_type:
        if not IS(obj, (ObjType, ClassType, DictType, Bind)):
            # other types doesn't have any attributes for now
            attribs.append(TypeError('unknown object for getattr', obj))
        elif obj.hasattr(attribute_name):
            # get the attribute itself
            attribs.extend(obj.getattr(attribute_name))
        else:
            attribs.append(TypeError('no such attribute', attribute_name))
    return attribs


# recursive function that collects all possible attributes
# for (inferred_value.attr1.attr2) attribute_stack is ['attr2', 'attr1']
def apply_attribute_chain(exp, inferred_value, attribute_stack):
    attribute_name = attribute_stack.pop()
    current_inferred_values = get_attribute(exp, inferred_value, attribute_name)
    debug('apply_attribute_chain:', attribute_name, '=',
          current_inferred_values)
    if attribute_stack:
        results = []
        # create a copy to avoid extra popping
        results.extend(apply_attribute_chain(exp, current_inferred_values, list(attribute_stack)))
        return results
    else:
        return current_inferred_values


def infer_attribute(exp, env, stk):
    value = exp.value
    attribute_chain = [exp.attr]
    while(IS(value, Attribute)):  # go to the first non-attribute
        # save attribute names along the way
        attribute_chain.append(value.attr)
        value = value.value
    inferred_value = infer(value, env, stk)
    if inferred_value:
        # apply the attribute chain
        attribs = []
        for attrib in apply_attribute_chain(exp, inferred_value, attribute_chain):
            attribs.append(attrib)
        debug("attribute infered:", attribs)
        return attribs
    else:
        return [UnknownType(exp)]


# main type inferencer
def infer(exp, env, stk):
    '@types: ast.AST|object, LinkedList, LinkedList -> list[Type]'
    debug('infering', exp, exp.__class__)
    assert exp is not None

    if IS(exp, Module):
        return infer(exp.body, env, stk)

    elif IS(exp, list):
        env = close(exp, env)
        (t, _) = inferSeq(exp, env, stk)   # env ignored (out of scope)
        return t

    elif IS(exp, Num):
        # we need objects, not types
        return (exp,)  # [PrimType(type(exp.n))]

    elif IS(exp, Str):
        # we need objects, not types
        return (exp,)  # [PrimType(type(exp.s))]

    elif IS(exp, Name):
        b = lookup(exp.id, env)
        debug('infering name:', b)#, env)
        if (b != None):
            putInfo(exp, b)
            return b
        else:
            try:
                t = eval(exp.id)  # try use information from Python interpreter
                return [PrimType(t)]
            except NameError as _:
                putInfo(exp, UnknownType(exp))
                return (UnknownType(exp),)

    elif IS(exp, Lambda):
        c = Closure(exp, env)
        for d in exp.args.defaults:
            dt = infer(d, env, stk)
            c.defaults.append(dt)
        return [c]

    elif IS(exp, Call):
        return invoke(exp, env, stk)

    elif IS(exp, Attribute):
        return tuple(infer_attribute(exp, env, stk))

    ## ignore complex types for now
    elif IS(exp, (List, Tuple)):
        eltTypes = []
        for e in exp.elts:
            t = infer(e, env, stk)
            eltTypes.extend(tuple(t))
        return [Bind(ListType(eltTypes), exp)]

    # elif IS(exp, Tuple):
    #     eltTypes = []
    #     for e in exp.elts:
    #         t = infer(e, env, stk)
    #         eltTypes.append(t)
    #     return [Bind(TupleType(eltTypes), exp)]

    elif IS(exp, ObjType):
        return exp

#    elif IS(exp, ast.List):
#        infered_elts = flatten([infer(el, env, stk) for el in exp.elts])
#        return [ListType(tuple(infered_elts))]

    elif IS(exp, ast.Dict):
        infered_keys = [infer(key, env, stk) for key in exp.keys]
        infered_values = [infer(value, env, stk) for value in exp.values]
        temp_dict = defaultdict(list)
        dic = nil
        for keys, value in zip(infered_keys, infered_values):
            for key in keys:
                try:
                    temp_dict[key] = value  # only the last value
                                            # with the same key is stored
                except TypeError, _:  # unhashable instance
                    dic = ext(key, value, dic)

        for key, value in temp_dict.iteritems():
            dic = ext(key, value, dic)
        return [DictType(dic)]

    elif IS(exp, ast.Subscript):
        types = []
        t = infer(exp.value, env, stk)
        for tt in t:
            if IS(tt, Bind):
                if IS(exp.slice, ast.Index):
                    types.extend(tt.typ.elts)
                else:
                    types.extend(t)
            elif IS(tt, DictType):
                subscript = infer(exp.slice, env, stk)
                types.extend(tt.get_key(subscript))
            else:
                types.append('PysonarError: %s of %s' % (UnknownType(exp), tt.__class__))
        return types

    elif IS(exp, ast.BinOp):
        return inferBinOp(exp, env, stk)

    else:
        return [UnknownType(exp)]


def inferBinOp(exp, env, stk):
    results = []
    if IS(exp.op, ast.Mod):
        lefts = infer(exp.left, env, stk)
        rights = infer(exp.right, env, stk)
        for left in lefts:
            if IS(left, Str):
                for right in rights:
                    if IS(right, Str):
                        results.append(left.s % right.s)
                    elif IS(right, UnknownType):
                        results.append(left.s)
                    else:
                        #results.append(left.s % right)
                        pass
            else:
                results.append(exp)
    else:
        results.append(exp)
    return tuple(results)


##################################################################
# drivers(wrappers)
##################################################################
# clean up globals
def clear():
    imported_modules.clear()
    history.clear()
    MYDICT.clear()
    global nUnknown
    nUnknown = 0


def nodekey(node):
    if hasattr(node, 'lineno'):
        return node.lineno
    else:
        return sys.maxint


# check a single (parsed) expression
def checkExp(exp):
    clear()
    addToPythonPath(os.path.dirname(sys.modules[__name__].__file__))
    ret = infer(exp, nil, nil)
    if history.keys() != [] and logger.isEnabledFor(logging.DEBUG):
        debug("---------------------------- history -------------------------")
        for k in sorted(history.keys(), key=nodekey):
            debug(k, ":", history[k])
        debug("\n")
    return ret


# check a string
def checkString(s):
    return checkExp(createAST(s))


# check a file
def checkFile(filename):
    return checkExp(parseFile(filename))


def parseFile(filename):
    f = open(filename, 'r')
    root_node = createAST(f.read(), filename)
    f.close()
    return root_node


def createAST(string, filename='<string>'):
    root_node = ast.parse(string)
    for node in ast.walk(root_node):
        node.filename = filename
    return root_node


def getModuleExp(modulename):
    modulename = modulename.replace('.', os.path.sep)
    for directory_name in PYTHONPATH:
        try:
            filename = os.path.join(directory_name, modulename + '.py')
            return parseFile(filename)
        except IOError, e:
            warn(str(e))
    return createAST('')


###################################################################
# hacky printing support for AST
###################################################################
def dump(node, annotate_fields=True, include_attributes=False):
    def _format(node):
        if isinstance(node, AST):
            fields = [(a, _format(b)) for a, b in iter_fields(node)]
            rv = '%s(%s' % (node.__class__.__name__, ', '.join(
                ('%s=%s' % field for field in fields)
                if annotate_fields else
                (b for a, b in fields)
            ))
            if include_attributes and node._attributes:
                rv += fields and ', ' or ' '
                rv += ', '.join('%s=%s' % (a, _format(getattr(node, a)))
                                for a in node._attributes)
            return rv + ')'
        elif isinstance(node, list):
            return '[%s]' % ', '.join(_format(x) for x in node)
        return repr(node)
    if not isinstance(node, AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)


def printList(ls):
    if (ls == None or ls == []):
        return ""
    elif (len(ls) == 1):
        return repr(ls[0])
    else:
        return repr(ls)


def printAst(node):
    # WARNING: repr should return a string, not unicode
    if (IS(node, Module)):
        ret = "module:" + repr(node.body)
    elif (IS(node, FunctionDef)):
        ret = "fun:" + repr(node.name)
    elif (IS(node, ClassDef)):
        ret = "class:" + repr(node.name)
    elif (IS(node, Attribute)):
        ret = "attribute:" + repr(node.value) + "." + repr(node.attr)
    elif (IS(node, Call)):
        ret = ("call:" + repr(node.func)
               + ":(" + printList(node.args) + ")")
    elif (IS(node, Assign)):
        ret = ("(" + printList(node.targets)
               + " <- " + printAst(node.value) + ")")
    elif (IS(node, If)):
        ret = ("if " + repr(node.test)
               + ":" + printList(node.body)
               + ":" + printList(node.orelse))
    elif (IS(node, Compare)):
        ret = (repr(node.left) + ":" + printList(node.ops)
               + ":" + printList(node.comparators))
    elif (IS(node, Name)):
        ret = str(node.id)
    elif (IS(node, Num)):
        ret = str(node.n)
    elif (IS(node, Str)):
        ret = repr(node.s)
    elif (IS(node, Return)):
        ret = "return " + repr(node.value)
    elif (IS(node, Print)):
        ret = ("print(" + (str(node.dest)
               + ", " if (node.dest != None) else "")
               + printList(node.values) + ")")
    elif (IS(node, Expr)):
        ret = "expr:" + str(node.value)
    elif (IS(node, BinOp)):
        ret = (str(node.left) + " "
               + str(node.op) + " "
               + str(node.right))
    elif (IS(node, Mult)):
        ret = '*'
    elif (IS(node, Add)):
        ret = '+'
    elif (IS(node, Pass)):
        ret = "pass"
    elif IS(node, Global):
        ret = "global:" + str(node.names)
    elif IS(node, Assert):
        ret = "assert " + str(node.test)
    elif IS(node, list):
        ret = printList(node)
    else:
        ret = str(type(node))
    if hasattr(node, 'lineno') and hasattr(node, 'filename'):
        if hasattr(node, 'filename'):
            return ret + '@' + node.filename + ':' + str(node.lineno)
        return (re.sub("@[0-9]+", '', ret)
                + "@" + str(node.lineno))
    else:
        return ret


def addToPythonPath(dirname):
    PYTHONPATH.append(dirname)

def addToIgnoredFiles(filename):
    FILES_TO_SKIP.add(filename)

def installPrinter():
    import inspect
    for _, obj in inspect.getmembers(ast):
        if (inspect.isclass(obj) and not (obj == AST)):
            obj.__repr__ = printAst

installPrinter()

if __name__ == '__main__':
    # test the checker on a file
    addToPythonPath(os.path.dirname(sys.argv[1]))
    checkFile(sys.argv[1])


def get_module_symbols(name):
    if name in imported_modules:
        return imported_modules.get(name)
    else:
        module = getModuleExp(name)
        env1 = close(module.body, nil)  # TODO refactor along with infer(list)
        _, module_symbols = inferSeq(module.body, env1, nil)
        imported_modules[name] = (module, module_symbols)
    return module, module_symbols

def lookup(identifier, env):
    obj = lists.lookup(identifier, env)
    if not obj:  # might be a built-in
        builtins = getModuleObject('__builtins__')
        obj = builtins.getattr(identifier)
        if not obj:
            obj = None
    return obj
