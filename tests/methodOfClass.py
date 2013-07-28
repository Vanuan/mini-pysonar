a = 'b'

class A():
    def func(self):
        return A.m()

    def m(self):
        return a


def func():
    a = 's'
    return A.func()

# we should see func() -> "b"
func()
