class Class:

    def __init__(self, errorMsg):
        self.errorMsg = errorMsg


class Class2:
    def __init__(self):
        # A significant performance penalty when
        # NameError is encountered        # CONSTANT = ''
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)
        Class(CONSTANT)


resolver = Class2()
resolver = Class2()
resolver = Class2()
resolver = Class2()
resolver = Class2()
resolver = Class2()
resolver = Class2()
