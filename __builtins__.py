def filter(function, iterable):
     return iterable  # simplified inference

def map(function, iterable):
    return [function(iterable[0])]  # simplified

def reduce(func, b, init=[]):
    return func(b[0])
