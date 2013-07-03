from globals import ObjectStateHolder

def create(className):
    return ObjectStateHolder(className, 'id')

def main(F):
    o = create('OSH')

main(F)
