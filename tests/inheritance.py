class A():
    def templateMethod(self):
        a = 'templateMethod'
        self.child()

class B(A):
    def child():
        a = 'a'

B().templateMethod()
