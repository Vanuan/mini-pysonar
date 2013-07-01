
class A():
    def templateMethod(self, templatearg):
        self.child('childArgFromTemplate')

    def parent(self, parentarg):
        self.parent2('parent2ArgFromParent')

    def parent2(self, parent2arg):
        pass

class B(A):
    def child(self, childarg):
        self.parent('parentArg')

b = B('Constructor parameter')
b.templateMethod('templateArg')
