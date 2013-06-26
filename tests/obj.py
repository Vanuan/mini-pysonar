class ObjectStateHolder(object):
    def setAttribute(name, val):
        pass
    def setIntAttribute(name, val):
        pass

class AttributeStateHolder(object):
    pass

o = ObjectStateHolder('Ooo')
o.setAttribute('attrname', 'val')
o.setIntAttribute('attrname1', 'val1')

o = ObjectStateHolder('Ooo1')
o.setAttribute('attrname3', 'val')
o.setIntAttribute('attrname4', 'val1')

o = ObjectStateHolder('AAA')
#o.setAttribute(AttributeStateHolder())
