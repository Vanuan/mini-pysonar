class A:
    def m(self, **kwargs):
        self.m(**kwargs)
        self.m2(kwargs)

    def m2(self, arg):
        pass

a = A()
a.m(key1='key1', key2='key2')
