import logging
log = logging.getLogger(__name__)

import copy

from atom.api import Atom, Bool, Enum, List, Unicode, Typed

################################################################################
# Core classes and utility functions
################################################################################
class PluginDescription(Atom):

    name = Unicode()
    title = Unicode()
    required = Bool()
    selected = Bool()
    manifest = Unicode()

    def copy(self, **kwargs):
        other = copy.copy(self)
        for k, v in kwargs.items():
            setattr(other, k, v)
        return other


class ParadigmDescription(Atom):

    name = Unicode()
    title = Unicode()
    plugins = List()
    type = Enum('ear', 'animal', 'cohort', 'calibration')

    def enable_plugin(self, plugin_name):
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                plugin.selected = True
                return
        valid_plugins = ', '.join(p.name for p in self.plugins)
        raise ValueError(f'Plugin {plugin_name} does not exist. ' \
                         f'Valid options are {valid_plugins}')

    def copy(self, **kwargs):
        other = copy.copy(self)
        for k, v in kwargs.items():
            setattr(other, k, v)
        return other


class ExperimentDescription(Atom):

    name = Unicode()
    title = Unicode()
    io_manifest = Unicode()
    paradigm = Typed(ParadigmDescription)


def get_experiments(type):
    return [e for e in experiments.values() if e.type == type]


################################################################################
# CFTS stuff
################################################################################
abr_io_controller = PluginDescription(
    name='controller',
    title='Controller',
    required=True,
    manifest='psi.application.experiment.abr_io.ABRIOManifest',
)


dpoae_time_controller = PluginDescription(
    name='controller',
    title='Controller',
    required=True,
    manifest='psi.application.experiment.dpoae_time.ControllerManifest',
)


dpoae_io_controller = PluginDescription(
    name='controller',
    title='Controller',
    required=True,
    manifest='psi.application.experiment.dpoae_io.ControllerManifest',
)


temperature_mixin = PluginDescription(
    name='temperature',
    title='Temperature display',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.TemperatureMixinManifest',
)


eeg_view_mixin = PluginDescription(
    name='eeg_view',
    title='EEG display',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.EEGViewMixinManifest',
)


abr_in_ear_calibration_mixin = PluginDescription(
    name='abr_in_ear_calibration',
    title='In-ear calibration',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.ABRInEarCalibrationMixinManifest',
)


dpoae_in_ear_calibration_mixin = PluginDescription(
    name='dpoae_in_ear_calibration',
    title='In-ear calibration',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.DPOAEInEarCalibrationMixinManifest',
)


dpoae_in_ear_noise_calibration_mixin = PluginDescription(
    name='dpoae_in_ear_noise_calibration',
    title='In-ear noise calibration',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.DPOAEInEarNoiseCalibrationMixinManifest',
)


microphone_signal_view_mixin = PluginDescription(
    name='microphone_signal_view',
    title='Microphone view (time)',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.MicrophoneSignalViewMixinManifest',
)


microphone_fft_view_mixin = PluginDescription(
    name='microphone_fft_view',
    title='Microphone view (PSD)',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.MicrophoneFFTViewMixinManifest',
)


abr_io_experiment = ParadigmDescription(
    name='abr_io',
    title='ABR (input-output)',
    type='ear',
    plugins=[
        abr_io_controller,
        temperature_mixin.copy(),
        eeg_view_mixin.copy(),
        abr_in_ear_calibration_mixin.copy(),
    ]
)


dpoae_time_noise_mixin = PluginDescription(
    name='dpoae_time_noise',
    title='Noise elicitor',
    required=False,
    selected=False,
    manifest='psi.application.experiment.cfts_mixins.DPOAETimeNoiseMixinManifest',
)


dpoae_time_ttl_mixin = PluginDescription(
    name='dpoae_ttl_noise',
    title='TTL output',
    required=False,
    selected=False,
    manifest='psi.application.experiment.cfts_mixins.DPOAETimeTTLMixinManifest',
)


eeg_mixin = PluginDescription(
    name='eeg_mixin',
    title='EEG',
    required=False,
    selected=False,
    manifest='psi.application.experiment.cfts_mixins.EEGMixinManifest',
)


dpoae_time_experiment = ParadigmDescription(
    name='dpoae_time',
    title='DPOAE (over time)',
    type='ear',
    plugins=[
        dpoae_time_controller,
        temperature_mixin.copy(),
        dpoae_in_ear_calibration_mixin.copy(),
        microphone_fft_view_mixin.copy(),
        microphone_signal_view_mixin.copy(selected=False),
        dpoae_time_noise_mixin.copy(),
        dpoae_in_ear_noise_calibration_mixin.copy(),
    ]
)


microphone_elicitor_fft_view_mixin = PluginDescription(
    name='microphone_elicitor_fft_view',
    title='Microphone view (PSD)',
    required=False,
    selected=True,
    manifest='psi.application.experiment.cfts_mixins.MicrophoneElicitorFFTViewMixinManifest',
)


dpoae_contra_experiment = ParadigmDescription(
    name='dpoae_contra',
    title='DPOAE (contra noise)',
    type='ear',
    plugins=[
        dpoae_time_controller,
        temperature_mixin.copy(),
        microphone_elicitor_fft_view_mixin.copy(),
        dpoae_time_noise_mixin.copy(required=True),
        dpoae_in_ear_calibration_mixin.copy(),
        dpoae_in_ear_noise_calibration_mixin.copy(),
    ]
)


dpoae_ttl_experiment = ParadigmDescription(
    name='dpoae_ttl',
    title='DPOAE (TTL output)',
    type='ear',
    plugins=[
        dpoae_time_controller,
        temperature_mixin.copy(),
        microphone_fft_view_mixin.copy(),
        dpoae_time_ttl_mixin.copy(required=True),
        dpoae_in_ear_calibration_mixin.copy(),
        eeg_mixin.copy(),
        eeg_view_mixin.copy(),
    ]
)


dpoae_io_experiment = ParadigmDescription(
    name='dpoae_io',
    title='DPOAE input-output',
    type='ear',
    plugins=[
        dpoae_io_controller,
        temperature_mixin.copy(),
        eeg_view_mixin.copy(),
        dpoae_in_ear_calibration_mixin.copy(),
        microphone_fft_view_mixin.copy(),
        microphone_signal_view_mixin.copy(),
    ]
)


################################################################################
# Calibration
################################################################################
golay_mixin = PluginDescription(
    name='golay',
    title='golay',
    required=True,
    manifest='psi.application.experiment.calibration_mixins.GolayMixin'
)


chirp_mixin = PluginDescription(
    name='chirp',
    title='Chirp',
    required=True,
    manifest='psi.application.experiment.calibration_mixins.ChirpMixin'
)


tone_mixin = PluginDescription(
    name='tone',
    title='Tone',
    required=True,
    manifest='psi.application.experiment.calibration_mixins.ToneMixin'
)


speaker_calibration_controller = PluginDescription(
    name='controller',
    title='Controller',
    required=True,
    manifest='psi.application.experiment.speaker_calibration.BaseSpeakerCalibrationManifest',
)


speaker_calibration_golay_experiment = ParadigmDescription(
    name='speaker_calibration_golay',
    title='Speaker calibration (Golay)',
    type='calibration',
    plugins=[
        speaker_calibration_controller,
        golay_mixin,
    ]
)


speaker_calibration_chirp_experiment = ParadigmDescription(
    name='speaker_calibration_chirp',
    title='Speaker calibration (chirp)',
    type='calibration',
    plugins=[
        speaker_calibration_controller,
        chirp_mixin,
    ]
)


speaker_calibration_tone_experiment = ParadigmDescription(
    name='speaker_calibration_tone',
    title='Speaker calibration (tone)',
    type='calibration',
    plugins=[
        speaker_calibration_controller,
        tone_mixin,
    ]
)


pistonphone_controller = PluginDescription(
    name='pistonphone_controller',
    title='Pistonphone controller',
    required=True,
    selected=True,
    manifest='psi.application.experiment.pistonphone_calibration.PistonphoneCalibrationManifest',
)


pistonphone_calibration = ParadigmDescription(
    name='pistonphone_calibration',
    title='Pistonphone calibration',
    type='calibration',
    plugins=[
        pistonphone_controller
    ],
)


golay_controller = PluginDescription(
    name='golay_controller',
    title='Golay controller',
    required=True,
    selected=True,
    manifest='psi.application.experiment.pt_calibration.GolayControllerManifest',
)


chirp_controller = PluginDescription(
    name='chirp_controller',
    title='Chirp controller',
    required=True,
    selected=True,
    manifest='psi.application.experiment.pt_calibration.ChirpControllerManifest',
)


pt_calibration_chirp = ParadigmDescription(
    name='pt_calibration_chirp',
    title='Probe tube calibration (chirp)',
    type='calibration',
    plugins=[
        chirp_controller,
    ],
)


pt_calibration_golay = ParadigmDescription(
    name='pt_calibration_golay',
    title='Probe tube calibration (golay)',
    type='calibration',
    plugins=[
        golay_controller,
    ],
)


################################################################################
# Noise exposure
################################################################################
noise_exposure_controller = PluginDescription(
    name='noise_exposure_controller',
    title='Noise exposure controller',
    required=True,
    selected=True,
    manifest='psi.application.experiment.noise_exposure.ControllerManifest',
)


noise_exposure_experiment = ParadigmDescription(
    name='noise_exposure',
    title='Noise exposure',
    type='cohort',
    plugins=[
        noise_exposure_controller,
    ],
)


################################################################################
# Behavior
################################################################################
appetitive_gonogo_controller = PluginDescription(
    name='appetitive_gonogo_controller',
    title='Appetitive GO-NOGO controller',
    required=True,
    selected=True,
    manifest='psi.application.experiment.appetitive.ControllerManifest',
)


pellet_dispenser_mixin = PluginDescription(
    name='pellet_dispenser',
    title='Pellet dispenser',
    required=False,
    selected=True,
    manifest='psi.application.experiment.behavior_base.PelletDispenserMixinManifest',
)


appetitive_experiment = ParadigmDescription(
    name='appetitive_gonogo_food',
    title='Appetitive GO-NOGO food',
    type='animal',
    plugins=[
        appetitive_gonogo_controller,
        pellet_dispenser_mixin,
    ],
)


################################################################################
# Wrapup
################################################################################
experiments = {
    'abr_io': abr_io_experiment,
    'dpoae_contra': dpoae_contra_experiment,
    'dpoae_ttl': dpoae_ttl_experiment,
    'dpoae_io': dpoae_io_experiment,
    'speaker_calibration_chirp': speaker_calibration_chirp_experiment,
    'speaker_calibration_tone': speaker_calibration_tone_experiment,
    'speaker_calibration_chirp_inear': speaker_calibration_chirp_experiment.copy(type='ear'),
    'speaker_calibration_tone_inear': speaker_calibration_tone_experiment.copy(type='ear'),
    'speaker_calibration_golay': speaker_calibration_golay_experiment,
    'appetitive_gonogo_food': appetitive_experiment,
    'noise_exposure': noise_exposure_experiment,
    'pistonphone_calibration': pistonphone_calibration,
    'pt_calibration_golay': pt_calibration_golay,
    'pt_calibration_chirp': pt_calibration_chirp,
}
