# pysonar.py - a Python version of PySonar static analyzer for Python
# Copyright (C) 2011 Yin Wang (yinwang0@gmail.com)


#-------------------------------------------------------------
# a library for Lisp lists
#-------------------------------------------------------------

class ListIterator:
    def __init__(self, p):
        self.p = p

    def next(self):
        if self.p == nil:
            raise StopIteration
#        elif (not isinstance(self.p, LinkedList)):
#            raise StopIteration
#            ret = self.p.snd
#            self.p = nil
#            return ret
        ret = self.p.fst
        self.p = self.p.snd
        return ret


class Nil:
    def __repr__(self):
        return "()"

    def __iter__(self):
        return ListIterator(self)

nil = Nil()


class SimplePair:
    def __init__(self, fst, snd):
        assert not isinstance(fst, LinkedList)
        self.fst = fst
        self.snd = snd

    def __repr__(self):
        return "(" + repr(self.fst) + " . " + repr(self.snd) + ")"

    def __eq__(self, other):
        if not isinstance(other, SimplePair):
            return False
        else:
            return self.fst == other.fst and self.snd == other.snd


class LinkedList:
    def __init__(self, fst, snd):
        self.fst = fst
        self.snd = snd
        self.__hash_table = {}
        if (isinstance(self.snd, Pair) and isinstance(self.fst, Pair)):
            #print self
            for p in self:
                if p != nil:
                    self.saveKeyValue(first(p), p)
            #print self.__hash_table

    def __repr__(self):
        return self.repr_with_limited_recursion(0)

    def repr_with_limited_recursion(self, counter):
        if counter < 100:
            counter = counter + 1
            if (self.snd == nil):
                return "(" + repr(self.fst) + ")"
            elif (isinstance(self.snd, LinkedList)):
                s = self.snd.repr_with_limited_recursion(counter)
                return "(" + repr(self.fst) + " " + s[1:-1] + ")"
            else:
                raise Exception('The second argument in LinkedList '
                                'should be LinkedList or nil')
        else:
            return '(LinkedList.__repr__: max recursion depth exceeded)'

    def __iter__(self):
        return ListIterator(self)

    def __eq__(self, other):
        if not isinstance(other, LinkedList):
            return False
        else:
            return self.fst == other.fst and self.snd == other.snd

    def saveKeyValue(self, key, value):
        try:
            self.__hash_table[key] = value
        except TypeError:
            pass

    def getKey(self, key):
        return self.__hash_table.get(key)

def first(p):
    return p.fst


def rest(p):
    return p.snd


def loner(u):
    return LinkedList(u, nil)


def foldl(f, x, ls):
    ret = x
    for y in ls:
        ret = f(ret, y)
    return ret


def length(ls):
    ret = 0
    for _ in ls:
        ret = ret + 1
    return ret


def remove(x, ls):
    ret = nil
    for y in ls:
        if x != y:
            ret = LinkedList(y, ret)
    return reverse(ret)


def assoc(u, v):
    return LinkedList(LinkedList(u, v), nil)


def slist(pylist):
    '''
    Make linked list using LinkedList of python list
    @types: iterable[T] -> LinkedList[T, LinkedList]'''
    ret = nil
    for i in xrange(len(pylist)):
        ret = LinkedList(pylist[len(pylist) - i - 1], ret)
    return ret


def pylist(ls):
    ret = []
    for x in ls:
        ret.append(x)
    return ret


def maplist(f, ls):
    ret = nil
    for x in ls:
        ret = LinkedList(f(x), ret)
    return reverse(ret)


def reverse(ls):
    ret = nil
    for x in ls:
        ret = LinkedList(x, ret)
    return ret


def filterlist(f, ls):
    ret = nil
    for x in ls:
        if f(x):
            ret = LinkedList(x, ret)
    return reverse(ret)


def append(*lists):
    def append1(ls1, ls2):
        ret = ls2
        for x in ls1:
            ret = LinkedList(x, ret)
        return ret
    return foldl(append1, nil, slist(lists))


def assq(x, s):
    if isinstance(s, Pair):
        p = s.getKey(x)
        if p:
            return p
    for p in s:
        if x == first(p):
            return p
    return None


def ziplist(ls1, ls2):
    ret = nil
    while ls1 != nil and ls2 != nil:
        ret = LinkedList(LinkedList(first(ls1), first(ls2)), ret)
        ls1 = rest(ls1)
        ls2 = rest(ls2)
    return reverse(ret)


# building association lists
def ext(x, v, s):
    return LinkedList(SimplePair(x, v), s)


def lookup(x, s):
    p = assq(x, s)
    if p != None:
        return rest(p)
    else:
        return None
