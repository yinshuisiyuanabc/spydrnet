from spydrnet.ir import *

hierarchical_seperator = "/"
bus_format = "[{}]"


def generate_virtual_instances_from_top_level_instance(top_instance):
    virtual_top_instance = VirtualInstance.from_instance(top_instance)
    return virtual_top_instance


class VirtualElement:
    _virtual_parent = None

    @property
    def virtual_parent(self):
        return self._virtual_parent

    @virtual_parent.setter
    def virtual_parent(self, value):
        self._virtual_parent = value

    @property
    def virtual_parents(self):
        parents = list()
        parent = self.virtual_parent
        while parent:
            parents.append(parent)
            parent = parent.virtual_parent
        return parents


class VirtualInstance(VirtualElement):

    @staticmethod
    def from_instance(instance):
        top_level = VirtualInstance()
        top_level.instance = instance
        definition = instance.definition
        search_stack = [(top_level, False)]
        while search_stack:
            virtualInstance, visited = search_stack.pop()
            instance = virtualInstance.instance
            definition = instance.definition
            if definition:
                if visited:
                    definition.virtual_instances.add(virtualInstance)
                else:
                    search_stack.append((virtualInstance, True))
                    sub_instances = definition.instances
                    for sub_instance in sub_instances:
                        child_virtual_instance = virtualInstance.create_virtual_child(sub_instance)
                        search_stack.append((child_virtual_instance, False))
                    ports = definition.ports
                    for port in ports:
                        virtualPort = virtualInstance.create_virtual_port(port)
                        for pin in port.inner_pins:
                            virtualPort.create_virtual_pin(pin)
                    cables = definition.cables
                    for cable in cables:
                        virtualCable = virtualInstance.create_virtual_cable(cable)
                        for wire in cable.wires:
                            virtualCable.create_virtual_wire(wire)
        return top_level

    def __init__(self):
        self.virtualParent = None
        self.instance = None
        self.virtualChildren = dict()
        self.virtualPorts = dict()
        self.virtualCables = dict()

    def __str__(self):
        return self.get_hierarchical_name()

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.get_hierarchical_name())

    def is_leaf(self):
        return self.instance.is_leaf()

    def create_virtual_child(self, instance):
        virtual_child = VirtualInstance()
        self.virtualChildren[instance] = virtual_child
        virtual_child.virtualParent = self
        virtual_child.instance = instance
        return virtual_child

    def create_virtual_port(self, port):
        virtualPort = VirtualPort()
        virtualPort.port = port
        virtualPort.virtualParent = self
        self.virtualPorts[port] = virtualPort
        return virtualPort
        
    def create_virtual_cable(self, cable):
        virtualCable = VirtualCable()
        virtualCable.cable = cable
        virtualCable.virtualParent = self
        self.virtualCables[cable] = virtualCable
        return virtualCable
        
    def get_hierarchical_name(self):
        names = [self.get_name()]
        parent = self.virtualParent
        while parent:
            names.append(parent.get_name())
            parent = parent.virtualParent
        return hierarchical_seperator.join(names[-2::-1])
        
    def get_name(self):
        if 'EDIF.original_identifier' in self.instance:
            name = self.instance['EDIF.original_identifier']
        else:
            name = self.instance['EDIF.identifier']
        return name


class VirtualPort:
    def __init__(self):
        self.virtualParent = None
        self.port = None
        self.virtualPins = dict()
        
    def create_virtual_pin(self, pin):
        virtualPin = VirtualPin()
        virtualPin.pin = pin
        virtualPin.virtualParent = self
        self.virtualPins[pin] = virtualPin
        return virtualPin

    @property
    def direction(self):
        return self.port.direction
        
    def get_hierarchical_name(self):
        prefix = self.virtualParent.get_hierarchical_name()
        return prefix + self.get_name()    
        
    def get_name(self):
        if 'EDIF.original_identifier' in self.port:
            name = self.port['EDIF.original_identifier']
        else:
            name = self.port['EDIF.identifier']
        return name        


class VirtualPin:
    def __init__(self):
        self.virtualParent = None
        self.pin = None
    
    @property
    def direction(self):
        return self.virtualParent.direction

    def get_outer_pin(self):
        virtualPort = self.virtualParent
        virtualInstance = virtualPort.virtualParent
        virtualParent = virtualInstance.virtualParent
        if virtualParent:
            if self.pin in virtualInstance.instance.outer_pins:
                outer_pin = virtualInstance.instance.outer_pins[self.pin]
                return outer_pin
            return None
        return None
        
    def get_outer_virtual_wire(self):
        virtualPort = self.virtualParent
        virtualInstance = virtualPort.virtualParent
        virtualParent = virtualInstance.virtualParent
        if virtualParent:
            if self.pin in virtualInstance.instance.outer_pins:
                outer_pin = virtualInstance.instance.outer_pins[self.pin]
                if outer_pin.wire is not None:
                    virtualCable = virtualParent.virtualCables[outer_pin.wire.cable]
                    virtualWire = virtualCable.virtualWires[outer_pin.wire]
                    return virtualWire
                return None
            return None
        return None
        
    def get_inner_virtual_wire(self):
        virtualPort = self.virtualParent
        virtualInstance = virtualPort.virtualParent
        wire = self.pin.wire
        if wire:
            cable = wire.cable
            virtualCable = virtualInstance.virtualCables[cable]
            virtualWire = virtualCable.virtualWires[wire]
            return virtualWire
        return None
        
    def get_hierarchical_name(self):
        prefix = self.virtualParent.get_hierarchical_name()
        if self.virtualParent.port.is_scalar:
            return prefix
        else:
            return prefix + bus_format.format("#")


class VirtualCable:
    def __init__(self):
        self.virtualParent = None
        self.cable = None
        self.virtualWires = dict()
 
    def create_virtual_wire(self, wire):
        virtualWire = VirtualWire()
        virtualWire.wire = wire
        virtualWire.virtualParent = self
        self.virtualWires[wire] = virtualWire
        return virtualWire
    
    def get_hierarchical_name(self):
        prefix = self.virtualParent.get_hierarchical_name()
        if prefix:
            return prefix + hierarchical_seperator + self.get_name()
        else:
            return self.get_name()
    
    def get_name(self):
        if 'EDIF.original_identifier' in self.cable:
            name = self.cable['EDIF.original_identifier']
        else:
            name = self.cable['EDIF.identifier']
        return name


class VirtualWire:
    def __init__(self):
        self.virtualParent = None
        self.wire = None
    
    def get_source_virtualPins(self):
        virtualPins = list()
        virtualCable = self.virtualParent
        virtualInstance = virtualCable.virtualParent
        pins = self.wire.pins
        for pin in pins:
            if isinstance(pin, InnerPin) and pin.port.direction == Port.Direction.IN:
                virtualPort = virtualInstance.virtualPorts[pin.port]
                virtualPin = virtualPort.virtualPins[pin]
                virtualPins.append(virtualPin)
            elif isinstance(pin, OuterPin) and pin.inner_pin.port.direction == Port.Direction.OUT:
                virtualSubInstance = virtualInstance.virtualChildren[pin.instance]
                virtualPort = virtualSubInstance.virtualPorts[pin.inner_pin.port]
                virtualPin = virtualPort.virtualPins[pin.inner_pin]
                virtualPins.append(virtualPin)
        return virtualPins
        
    def get_sink_virtualPins(self):
        virtualPins = list()
        virtualCable = self.virtualParent
        virtualInstance = virtualCable.virtualParent
        pins = self.wire.pins
        for pin in pins:
            if isinstance(pin, InnerPin) and pin.port.direction == Port.Direction.OUT:
                virtualPort = virtualInstance.virtualPorts[pin.port]
                virtualPin = virtualPort.virtualPins[pin]
                virtualPins.append(virtualPin)
            elif isinstance(pin, OuterPin) and pin.inner_pin.port.direction == Port.Direction.OUT:
                virtualSubInstance = virtualInstance.virtualChildren[pin.instance]
                virtualPort = virtualSubInstance.virtualPorts[pin.inner_pin.port]
                virtualPin = virtualPort.virtualPins[pin.inner_pin]
                virtualPins.append(virtualPin)
        return virtualPins

    def get_virtualPins(self):
        virtualPins = list()
        virtualCable = self.virtualParent
        virtualInstance = virtualCable.virtualParent
        pins = self.wire.pins
        for pin in pins:
            if isinstance(pin, InnerPin):
                virtualPort = virtualInstance.virtualPorts[pin.port]
                virtualPin = virtualPort.virtualPins[pin]
                virtualPins.append(virtualPin)
            elif isinstance(pin, OuterPin):
                virtualSubInstance = virtualInstance.virtualChildren[pin.instance]
                virtualPort = virtualSubInstance.virtualPorts[pin.inner_pin.port]
                virtualPin = virtualPort.virtualPins[pin.inner_pin]
                virtualPins.append(virtualPin)
        return virtualPins

    def get_hierarchical_name(self):
        prefix = self.virtualParent.get_hierarchical_name()
        if self.virtualParent.cable.is_scalar:
            return prefix
        else:
            return prefix + bus_format.format("#")