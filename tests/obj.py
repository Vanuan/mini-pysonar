from globals import ObjectStateHolder

def main(F):

    creds = F.getCreds()
    for cred in creds:
        cred.get()
        o = ObjectStateHolder('OSH1')
        o.setAttribute('attr1', 'val1')
        o.setIntAttribute('attr2', 'val2')
        other(o)

        o = ObjectStateHolder('Ooo1')
        o.setAttribute('attrname3', 'val')
        o.setIntAttribute('attrname4', 'val1')

        o = ObjectStateHolder('AAA')
        #o.setAttribute(AttributeStateHolder())

def other(osh):
    osh.setAttribute('OSH attr3')

main(F)
