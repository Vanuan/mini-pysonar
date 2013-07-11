# pysonar.py - a Python version of PySonar static analyzer for Python
# Copyright (C) 2011 Yin Wang (yinwang0@gmail.com)
import sys
import re
import ast
from ast import *
from lists import lookup, nil, ext, first, rest, assq, reverse, maplist,\
    SimplePair, append

from collections import defaultdict
import os
import logging
from functools import partial

logging.basicConfig(filename="_pysonar.log", level=logging.ERROR)
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
        for base in bases:
            if IS(base, Attribute) or base.id == 'object':
                continue
            baseClasses = lookup(base.id, env)
            if (baseClasses and len(baseClasses) == 1
                and IS(baseClasses[0], ClassType)):
                # limit to one possible type
                baseClass = baseClasses[0]
                for key, val in baseClass.attrs.iteritems():
                    self.attrs[key] = val
            else:
                logger.error('Can\'t infer base of %s: %s %s'
                             % (name, baseClasses, base.id))
        self.__saveClassAttrs(body)

    def __saveClassAttrs(self, body):
        env = close(body, nil)  # {Name.id -> (Closure | ClassType)}
        for pair in env:
            # Closure's env will be updated, when invoking AttrType
            self.attrs[pair.fst] = pair.snd

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
            self.attrs[name] = attr
        self.ctorargs = ctorargs
        self.ast = ast

    def __repr__(self):
        return ("'" + str(self.classtype.name) + "' instance"  # +", ctor:" +
                #str(self.ctorargs) + ", attrs:" + str(self.attrs)
                )

    def __eq__(self, other):
        if IS(other, ObjType):
            return ((self.classtype == other.classtype) and
                    self.attrs == other.attrs)
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

class AttrType(Type):
    '''
    This is an analog to Name, just for object attributes

    Reference on object attribute value, so binds object with this value while
    name is determined in the context (or environment)
    '''
    def __init__(self, closures, o, objT):
        '''@types: list[Closure], ObjType, ast.AST
        @param: objT is a value of ast.Attribute
        '''
        # self.env = closure.env
        assert IS(closures, (list, tuple))
        self.clo = closures
        self.obj = o
        self.objT = objT

    def __repr__(self):
        clo_repr = ','.join(map(str, self.clo))
        return '(attr "%s", "%s")' % (self.obj, clo_repr)

    def __eq__(self, other):
        if IS(other, FuncType):
            return (self.clo == other.clo)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(tuple(self.clo)) + hash(self.objT)


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
        return "tup:" + str(self.elts)

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
    def __init__(self, elts):
        '@types: tuple'
        self.elts = elts

    def __repr__(self):
        return "list:" + str(self.elts)

    def __eq__(self, other):
        return (IS(other, ListType)
                and self.elts == other.elts)

    def __hash__(self):
        return hash(self.elts)

    def __iter__(self):
        return iter(self.elts)

    def __ne__(self, other):
        return not self.__eq__(other)


def flatten(list_of_lists):
    # TODO: handle __iter__ and next()
    flattened = []
    for sublist in list_of_lists:
        if not isinstance(sublist, TypeError):
            try:
                flattened.extend([i for i in sublist])
            except TypeError:
                flattened.append(sublist)
        else:
            flattened.append(sublist)
    return flattened


class DictType(Type):

    def __init__(self, dict_):
        '@types: LinkedList'
        self.dict = dict_
        self.attrs = {'keys': [self.get_keys],
                      'iterkeys': [self.get_keys],
                      'values': [self.get_values],
                      'itervalues': [self.get_values],
                      'items': [self.get_items],
                      'iteritems': [self.get_items],
                      'get': [self.get_key]}
        self.iter_operations = (self.get_keys, self.get_values, self.get_items)

    # Since we are not infering body's,
    # these functions should always return a list:

    @staticmethod
    def get_key(dict_, key, default=None):
        '@types: LinkedList, ? -> list'
        # potentially, any value can be returned
        value = flatten([key_value_pair.snd for key_value_pair in dict_])
        if default:
            value.extend(default)
        return value

    @staticmethod
    def get_keys(dict_):
        '@types: LinkedList -> list'
        return [[key_value_pair.fst for key_value_pair in dict_]]

    @staticmethod
    def get_values(dict_):
        '@types: LinkedList -> list'
        return [[key_value_pair.snd for key_value_pair in dict_]]

    @staticmethod
    def get_items(dict_):
        '@types: LinkedList -> list'
        return [[TupleType([[pair.fst], pair.snd]) for pair in dict_]]

    def __repr__(self):
        return "dict:" + str(self.dict)

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
        return "U:" + str(self.elts)


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
    for t in ts:
        if IS(t, (list, tuple)):                 # already a union (list)
            for b in t:
                #print b.__class__
                if b:
                    u.add(b)
                #if b not in u:
                #    u.append(b)
        else:
            if t:
                #print t.__class__
                u.add(t)
            #if t not in u:
            #    u.append(t)
    return list(u)


####################################################################
## type inferencer
####################################################################
class Bind:
    def __init__(self, typ, loc):
        self.typ = typ
        self.loc = loc

    def __repr__(self):
        return "(" + str(self.typ) + " <~~ " + str(self.loc) + ")"

    def __iter__(self):
        return BindIterator(self)

    def __eq__(self, other):
        return (IS(other, Bind) and
                self.typ == other.typ and
                self.loc == other.loc)


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
# only assocs appear in both envs are preserved
# use a variable bound in only one branch will cause type error
def mergeEnv(env1, env2):
    ret = nil
    for p1 in env1:
        p2 = assq(first(p1), env2)
        if p2 != None:
            ret = ext(first(p1), union([rest(p1), rest(p2)]), ret)
    return ret


# compare both str's and Name's for equivalence, because
# keywords are str's (bad design of the ast)
def getId(x):
    if IS(x, Name):
        return x.id
    else:
        return x


def getName(x, lineno):
    return Name(id=x, lineno=lineno)


def bind(target, infered_value, env):
    if IS(target, Name) or IS(target, str):
        u = infered_value
        putInfo(target, u)
        return ext(getId(target), u, env)
    elif IS(target, Attribute):
        ast_name = target.value
        infered_targets = infer(ast_name, env, nil)
        for obj in infered_targets:
            if IS(obj, (ClassType, ObjType)):
                obj.attrs[target.attr] = infered_value
            elif IS(obj, AttrType):
                obj.obj.attrs[target.attr] = infered_value
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
            env = bind(key, value, env)
        return env

    elif IS(target, ast.Subscript):
        error("Syntax error: Subscript type is not supported in assignment: ",
              target)
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


def saveMethodInvocationInfo(call, clo, env, stk):
    '''
    @types: ast.Call, ObjType, LinkedList, LinkedList -> None
    '''
    if call.args:
        ctorargs = [a for a in clo.obj.ctorargs]
        callargs = [infer(arg, env, stk) for arg in call.args]
        # TODO save keywords
        MYDICT[clo.obj.classtype.name].append((ctorargs, callargs, env))


def getMethodInvocationInfo():
    return MYDICT


# invoke one closure
def invoke1(call, clo, env, stk):
    '''@types: ast.Call, Callable, LinkedList, LinkedList -> ast.AST or Type
    '''
    if (clo == bottomType):
        return [bottomType]

    # Even if operator is not a closure, resolve the
    # arguments for partial information.
    if not IS(clo, (Closure, ClassType, AttrType)):
        # infer arguments even if it is not callable
        # (we don't know which method it is)
        debug('Unknown function or method, infering arguments', call.args)
        for a in call.args:
            infer(a, env, stk)
        for k in call.keywords:
            infer(k.value, env, stk)
        err = TypeError('calling non-callable', clo)
        putInfo(call, err)
        return [err]
    if IS(clo, ClassType):
        debug('creating instance of', clo)
        ctorargs = [infer(arg, env, stk) for arg in call.args]
        new_obj = ObjType(clo, ctorargs, clo.env, call)
        init_closures = new_obj.attrs.get('__init__', [])
        if len(init_closures):
            # we don't really care about this name,
            # we just don't want to collide with method's global symbols
            # TODO: generate a special name,
            #       that would represent a temporary object
            self_arg = get_self_arg_name(init_closures[0].func)
            ref_to_init = AttrType(init_closures, new_obj, self_arg)
            init_env = ext(self_arg.id, [new_obj], env)
            invoke1(call, ref_to_init, init_env, stk)
        return [new_obj]
    if IS(clo, AttrType):
        attr = clo
        if IS(attr.obj, ObjType):
            # add self to function call args
            actualParams = list(call.args)
            classtype = attr.obj.classtype
            saveMethodInvocationInfo(call, attr, env, stk)
            # TODO: @staticmethod, @classmethod
            if classtype.name != 'module':
                actualParams.insert(0, attr.objT)
            types = []
            for closure in attr.clo:
                if IS(closure, Closure):
                    # Create new env for method
                    # On each call ClassType.env might be different
                    new_closure = Closure(closure.func, classtype.env)
                    debug('invoking method', closure.func.name,
                          'with args', call.args)
                    types.extend(invokeClosure(call, actualParams, new_closure,
                                               env, stk))
                elif IS(closure, ClassType):
                    types.extend(invoke1(call, closure, env, stk))
                else:
                    types.append(TypeError("Callable type %s is not supported"
                                           % closure))
            return types
        elif IS(attr.obj, DictType):
            types = []
            for closure in attr.clo:
                if closure in attr.obj.iter_operations:
                    types.extend(closure(attr.obj.dict))
                else:
                    # we take the first version of infered arguments
                    # but ideally all must be processed
                    infered_args = [infer(arg, env, stk) for arg in call.args]
                    types.extend(closure(attr.obj.dict, *infered_args))
            return types
        else:
            err = TypeError('AttrType object is not supported for the invoke',
                            attr)
            putInfo(call, err)
            return [err]
    return invokeClosure(call, call.args, clo, env, stk)


def get_self_arg_name(fn_def):
    ''' Expecting to get ast.Name with id, for instance, self
    @types: ast.FunctionDef -> ast.Name
    '''
    if not fn_def.args.args:
        raise ValueError("Bound method has at least one parameter - self")
    arg = fn_def.args.args[0]
    if IS(arg, ast.Name):
        return arg
    msg = "Method definition %s doesn't have self as first argument"
    raise ValueError(msg % fn_def.name)


def invokeClosure(call, actualParams, clo, env, stk):
    '''
    @types: ast.Call, list[ast.AST], Closure, LinkedList, LinkedList -> list[Type]
    '''
    debug('invoking closure', clo.func, 'with args', actualParams)
    debug(clo.func.body)

    func = clo.func
    fenv = clo.env
    pos = nil
    kwarg = nil

    # bind positionals first
    poslen = min(len(func.args.args), len(actualParams))
    for i in xrange(poslen):
        t = infer(actualParams[i], env, stk)
        pos = bind(func.args.args[i], t, pos)

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
                ts = ts + t
            pos = bind(func.args.vararg, ts, pos)

    # bind keywords, collect kwarg
    ids = map(getId, func.args.args)
    for k in call.keywords:
        ts = infer(k.value, env, stk)
        tloc1 = lookup(k.arg, pos)
        if tloc1 != None:
            putInfo(call, TypeError('multiple values for keyword argument',
                                     k.arg, tloc1))
        elif k.arg not in ids:
            kwarg = bind(k.arg, ts, kwarg)
        else:
            pos = bind(k.arg, ts, pos)

    # put extras in kwarg or report them
    # bind call.keywords to func.args.kwarg
    if kwarg != nil:
        if func.args.kwarg != None:
            pos = bind(func.args.kwarg, [DictType(reverse(kwarg))], pos)
        else:
            putInfo(call, TypeError("unexpected keyword arguements", kwarg))
    elif func.args.kwarg != None:
        pos = bind(func.args.kwarg, [DictType(nil)], pos)

    # bind defaults, avoid overwriting bound vars
    # types for defaults are already inferred when the function was defined
    i = len(func.args.args) - len(func.args.defaults)
    _ = len(func.args.args)
    for j in xrange(len(clo.defaults)):
        tloc = lookup(getId(func.args.args[i]), pos)
        if tloc == None:
            pos = bind(func.args.args[i], clo.defaults[j], pos)
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
        totypes = totypes + list(t)
    return totypes


# pre-bind names to functions in sequences
def close(code_block, env):
    '''@types: list[ast.AST], LinkedList -> LinkedList'''
    for e in code_block:
        if IS(e, FunctionDef):
            c = Closure(e, nil)
            env = ext(e.name, [c], env)
        elif IS(e, ClassDef):
            c = ClassType(e.name, e.bases, e.body, nil, e)
            env = ext(e.name, [c], env)
        # here we also need Import and Assign
        # Assign is complicated
    return env


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
        env = bind(e.target, value, env)
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
            env = bind(x, t, env)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, AugAssign):
        t = infer(e.value, env, stk)
        env = bind(e.target, t, env)
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
            t1 = [PrimType(None)]
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
            env = bind(getName(name_import_as, e.lineno), module_symbol, env)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, Import):
        for module_name in e.names:
            name_to_import = module_name.name
            module, module_env = get_module_symbols(name_to_import)
            name_import_as = module_name.asname or module_name.name
            module_class = ClassType('module', [], module.body, module_env, e)
            module_obj = [ObjType(module_class, [], nil, e)]
            env = bind(getName(name_import_as, e.lineno), module_obj, env)
        return inferSeq(exp[1:], env, stk)

    elif IS(e, ClassDef):
        cs = lookup(e.name, env)
        if not cs:
            debug('Class def %s not found in scope %s' % (e.name, env))
        for c in cs:
            c.env = env

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

    elif IS(e, ast.Subscript):
        return inferSeq(exp[1:], env, stk)

    elif IS(e, ast.Exec):
        return inferSeq(exp[1:], env, stk)

    else:
        raise TypeError('recognized node in effect context', e)


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
        return [exp]  # [PrimType(type(exp.n))]

    elif IS(exp, Str):
        # we need objects, not types
        return [exp]  # [PrimType(type(exp.s))]

    elif IS(exp, Name):
        b = lookup(exp.id, env)
        debug('infering name:', b, env)
        if (b != None):
            putInfo(exp, b)
            return b
        else:
            try:
                t = eval(exp.id)  # try use information from Python interpreter
                return [PrimType(t)]
            except NameError as _:
                putInfo(exp, UnknownType(exp))
                return [UnknownType(exp)]

    elif IS(exp, Lambda):
        c = Closure(exp, env)
        for d in exp.args.defaults:
            dt = infer(d, env, stk)
            c.defaults.append(dt)
        return [c]

    elif IS(exp, Call):
        return invoke(exp, env, stk)

    elif IS(exp, Attribute):
        t = infer(exp.value, env, stk)
        if t:
            attribs = []
            # find attr name in object and return it
            for o in t:
                if not IS(o, (ObjType, ClassType, DictType)):
                    attribs.append(TypeError('unknown object', o))
                    continue
                if exp.attr in o.attrs:
                    attribs.append(AttrType(o.attrs[exp.attr], o, exp.value))
                else:
                    attribs.append(TypeError('no such attribute', exp.attr))
            return attribs
        else:
            return [UnknownType(exp)]

    ## ignore complex types for now
    # elif IS(exp, List):
    #     eltTypes = []
    #     for e in exp.elts:
    #         t = infer(e, env, stk)
    #         eltTypes.append(t)
    #     return [Bind(ListType(eltTypes), exp)]

    # elif IS(exp, Tuple):
    #     eltTypes = []
    #     for e in exp.elts:
    #         t = infer(e, env, stk)
    #         eltTypes.append(t)
    #     return [Bind(TupleType(eltTypes), exp)]

    elif IS(exp, ObjType):
        return exp

    elif IS(exp, ast.List):
        infered_elts = flatten([infer(el, env, stk) for el in exp.elts])
        return [ListType(tuple(infered_elts))]

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

    else:
        return [UnknownType(exp)]


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
    if PYTHONPATH:
        directory_name = PYTHONPATH[0]
    else:
        directory_name = '.'
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
        return str(ls[0])
    else:
        return str(ls)


def printAst(node):
    if (IS(node, Module)):
        ret = "module:" + str(node.body)
    elif (IS(node, FunctionDef)):
        ret = "fun:" + str(node.name)
    elif (IS(node, ClassDef)):
        ret = "class:" + str(node.name)
    elif (IS(node, Attribute)):
        ret = "attribute:" + str(node.value) + "." + str(node.attr)
    elif (IS(node, Call)):
        ret = ("call:" + str(node.func)
               + ":(" + printList(node.args) + ")")
    elif (IS(node, Assign)):
        ret = ("(" + printList(node.targets)
               + " <- " + printAst(node.value) + ")")
    elif (IS(node, If)):
        ret = ("if " + str(node.test)
               + ":" + printList(node.body)
               + ":" + printList(node.orelse))
    elif (IS(node, Compare)):
        ret = (str(node.left) + ":" + printList(node.ops)
               + ":" + printList(node.comparators))
    elif (IS(node, Name)):
        ret = str(node.id)
    elif (IS(node, Num)):
        ret = str(node.n)
    elif (IS(node, Str)):
        ret = '"' + str(node.s) + '"'
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

imported_modules = {}


def get_module_symbols(name):
    if name in imported_modules:
        return imported_modules.get(name)
    else:
        module = getModuleExp(name)
        env1 = close(module.body, nil)  # TODO refactor along with infer(list)
        _, module_symbols = inferSeq(module.body, env1, nil)
        imported_modules[name] = (module, module_symbols)
    return module, module_symbols
