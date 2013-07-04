class Obj():
    def method(self, arg):
        pass

class Context():

    def __enter__(self):
        return Obj()

    def __exit__(self, type, value, traceback):
        # clean up
        pass

with Context() as f:
    f.method('something')
