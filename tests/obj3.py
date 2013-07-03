from globals import ObjectStateHolder

def create(className):
    return ObjectStateHolder(className)

def main(F):
    o = create('OSH')
    o.setAttribute('attrName', 'val')

main(F)
