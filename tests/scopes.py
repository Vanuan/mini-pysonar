
def g():
    return f()

a = 'global'

g()


def f():
    return a
