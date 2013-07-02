class A():
    def method(self, methodArgName):
        self.method('arg from method')

a = A('Constructor parameter')
a.method('arg from main')
