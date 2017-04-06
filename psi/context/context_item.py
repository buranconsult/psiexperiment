import numpy as np

from enaml.core.declarative import Declarative, d_
from atom.api import (Unicode, Typed, Value, Enum, List, Event, Property,
                      observe)

from .. import SimpleState


class ContextItem(SimpleState, Declarative):
    '''
    Defines the core elements of a context item. These items are made available
    to the context namespace.
    '''
    # Must be a valid Python identifier. Used by eval() in expressions.
    name = d_(Unicode())

    # Long-format label for display in the GUI. Include units were applicable.
    label = d_(Unicode())

    # Datatype of the value. Required for properly initializing some data
    # plugins (e.g., those that save data to a HDF5 file).
    dtype = d_(Unicode())

    # Name of the group to display the item under.
    group = d_(Unicode()).tag(transient=True)

    # Compact label where there is less space in the GUI (e.g., under a column
    # heading for example).
    compact_label = d_(Unicode())

    # Attributes to compare to determine equality of two items.
    _cmp_attrs = ['name']

    updated = Event()

    def _default_label(self):
        return self.name.capitalize()

    def _default_compact_label(self):
        return self.label

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        for attr in self._cmp_attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def coerce_to_type(self, value):
        coerce_function = np.dtype(self.dtype).type
        return coerce_function(value)

    def __hash__(self):
        return id(self)


class Result(ContextItem):
    '''
    A context item whose value is set by the plugin that contributes it. Typical
    use-cases include results calculated (e.g., reaction time, hit vs miss)
    following completion of a trial. These values are made available to the next
    iteration of the context.
    '''
    pass


class Parameter(ContextItem):
    '''
    A context item that can be evaluated dynamically, but cannot be included as
    part of a selector.  This is typically used for settings that must be
    determined before values are drawn from the selectors (e.g., probability of
    a go trial).
    '''
    # Default value of the context item when used as part of a selector.
    default = d_(Value())

    # Expression used to determine value of item.
    expression = d_(Unicode())

    # Defines the span over which the item's value does not change:
    # * experiment - the value cannot change once the experiment begins
    # * trial - The value cannot change once a trial begins. This is the only
    #   type of item that can be roved using a selector.
    # * arbitrary - The value can be changd at any time but it does not make
    #   sense for it to be a roving item.
    scope = d_(Enum('trial', 'experiment', 'arbitrary'))

    _cmp_attrs = ContextItem._cmp_attrs + ['expression']

    def _default_expression(self):
        return str(self.default)

    def _default_dtype(self):
        return np.array(self.default).dtype.str

    @observe('expression')
    def _notify_update(self, event):
        self.updated = event


class EnumParameter(Parameter):

    expression = Property().tag(transient=True)
    choices = d_(Typed(dict))
    selected = d_(Unicode())

    def _default_dtype(self):
        return np.array(self.choices.values()).dtype.str

    def _get_expression(self):
        try:
            return self.choices[self.selected]
        except:
            return None

    def _set_expression(self, expression):
        for k, v in self.choices.items():
            if v == expression:
                self.selected = k
                break
        else:
            if expression is not None:
                m = 'Could not map expression {} to choice'.format(expression)
                raise ValueError(m)

    @observe('selected')
    def _notify_update(self, event):
        self.updated = event


class FileParameter(Parameter):

    expression = Property().tag(transient=True)
    path = d_(Unicode())
    file_mode = d_(Enum('any_file', 'existing_file', 'directory'))
    current_path = d_(Unicode())
    name_filters = d_(List(Unicode()))

    def _get_expression(self):
        return '"{}"'.format(self.path)

    def _set_expression(self, expression):
        self.path = expression.strip('\"\'')

    @observe('path')
    def _notify_update(self, event):
        self.updated = event


class BoolParameter(Parameter):

    dtype = np.bool
