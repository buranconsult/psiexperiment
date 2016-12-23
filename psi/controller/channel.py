import logging
log = logging.getLogger(__name__)

import numpy as np

from atom.api import Unicode, Enum, Typed, Tuple, Property
from enaml.core.api import Declarative, d_

from .calibration import Calibration

from psi import SimpleState


class Channel(SimpleState, Declarative):

    label = d_(Unicode())

    # Device-specific channel identifier.
    channel = d_(Unicode())

    # For software-timed channels, set sampling frequency to 0.
    fs = d_(Typed(object))

    # Can be blank for no start trigger (i.e., acquisition begins as soon as
    # task begins)
    start_trigger = d_(Unicode())

    # Used to properly configure data storage.
    dtype = d_(Typed(np.dtype))

    engine = Property().tag(transient=True)

    calibration = d_(Typed(Calibration))


    def _get_engine(self):
        return self.parent

    def _set_engine(self, engine):
        self.set_parent(engine)

    def configure(self, plugin):
        pass


class AIChannel(Channel):

    TERMINAL_MODES = 'pseudodifferential', 'differential', 'RSE', 'NRSE'

    inputs = Property().tag(transient=True)
    expected_range = d_(Tuple())
    terminal_mode = d_(Enum(*TERMINAL_MODES))
    terminal_coupling = d_(Enum(None, 'AC', 'DC', 'ground'))

    def _get_inputs(self):
        return self.children

    def configure(self, plugin):
        for input in self.inputs:
            log.debug('Configuring input {}'.format(input.name))
            input.configure(plugin)


class AOChannel(Channel):
    '''
    An analog output channel supports one continuous and multiple epoch
    outputs.
    '''
    TERMINAL_MODES = 'pseudodifferential', 'differential', 'RSE'

    outputs = Property().tag(transient=True)
    expected_range = d_(Tuple())
    terminal_mode = d_(Enum(*TERMINAL_MODES))

    def _get_output_map(self):
        mapping = {
        for output in self.outputs:

    def _get_outputs(self):
        return self.children

    def configure(self, plugin):
        for output in self.outputs:
            log.debug('Configuring output {}'.format(output.name))
            output.configure(plugin)


class DIChannel(Channel):

    inputs = Property().tag(transient=True)

    def _get_inputs(self):
        return self.children

    def configure(self, plugin):
        for input in self.inputs:
            input.configure(plugin)


class DOChannel(Channel):

    outputs = Property().tag(transient=True)

    def _get_outputs(self):
        return self.children

    def configure(self, plugin):
        for output in self.outputs:
            output.configure(plugin)
