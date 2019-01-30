import os.path
from fractions import gcd
from pathlib import Path

import bcolz

from scipy.interpolate import interp1d
from scipy import signal
import numpy as np
import pandas as pd

import logging
log = logging.getLogger(__name__)

from atom.api import Atom, Callable, Float, Property, Typed, Value
from enaml.core.api import Declarative, d_
from psi import SimpleState

from . import util

from psi import get_config

################################################################################
# Exceptions
################################################################################
mesg = '''
Unable to run the calibration. Please double-check that the microphone and
speaker amplifiers are powered on and that the devices are positioned properly.
If you keep receiving this message, the microphone and/or the speaker may have
gone bad and need to be replaced.

{}
'''
mesg = mesg.strip()


thd_err_mesg = 'Total harmonic distortion for {:.1f}Hz is {:.1f}%'
nf_err_mesg = 'Power at {:.1f}Hz has SNR of {:.2f}dB'


class CalibrationError(Exception):

    def __str__(self):
        return self.message


class CalibrationTHDError(CalibrationError):

    def __init__(self, frequency, thd):
        self.frequency = frequency
        self.thd = thd
        self.base_message = thd_err_mesg.format(frequency, thd)
        self.message = mesg.format(self.base_message)


class CalibrationNFError(CalibrationError):

    def __init__(self, frequency, snr):
        self.frequency = frequency
        self.snr = snr
        self.base_message = nf_err_mesg.format(frequency, snr)
        self.message = mesg.format(self.base_message)


################################################################################
# Calibration routines
################################################################################
class Calibration(Atom):
    '''
    Assumes that the system is linear for a given frequency

    Parameters
    ----------
    frequency : 1D array
        Frequencies that system sensitivity was measured at.
    sensitivity : 1D array
        Sensitivity of system in dB(V/Pa).
    '''
    source = Value()

    @classmethod
    def as_attenuation(cls, vrms=1, **kwargs):
        '''
        Allows levels to be specified in dB attenuation
        '''
        return cls.from_spl([0, 100e3], [0, 0], vrms, **kwargs)

    @classmethod
    def from_magnitude(cls, frequency, magnitude, vrms=1, **kwargs):
        '''
        Generates a calibration object based on the recorded magnitude (Pa)

        Parameters
        ----------
        frequency : array-like
            List of freuquencies (in Hz)
        magnitude : array-like
            List of magnitudes (e.g., speaker output in Pa) for the specified
            RMS voltage.
        vrms : float
            RMS voltage (in Volts)

        Additional kwargs are passed to the class initialization.
        '''
        sensitivity = util.db(vrms)-util.db(magnitude)-util.db(20e-6)
        return cls(frequency, sensitivity, **kwargs)

    @classmethod
    def from_spl(cls, frequency, spl, vrms=1, **kwargs):
        '''
        Generates a calibration object based on the recorded SPL

        Parameters
        ----------
        frequency : array-like
            List of freuquencies (in Hz)
        spl : array-like
            List of magnitudes (e.g., speaker output in SPL) for the specified
            RMS voltage.
        vrms : float
            RMS voltage (in Volts)

        Additional kwargs are passed to the class initialization.
        '''
        sensitivity = util.db(vrms)-spl-util.db(20e-6)
        return cls(frequency, sensitivity, **kwargs)

    def get_spl(self, frequency, voltage):
        sensitivity = self.get_sens(frequency)
        return util.db(voltage)-sensitivity-util.db(20e-6)

    def get_sf(self, frequency, spl, attenuation=0):
        sensitivity = self.get_sens(frequency)
        vdb = sensitivity+spl+util.db(20e-6)+attenuation
        return 10**(vdb/20.0)

    def get_attenuation(self, frequency, voltage, level):
        return self.get_spl(frequency, voltage)-level

    def set_fixed_gain(self, fixed_gain):
        self.fixed_gain = fixed_gain

    def get_sens(self, frequency):
        raise NotImplementedError


class FlatCalibration(Calibration):

    sensitivity = Float().tag(metadata=True)
    fixed_gain = Float().tag(metadata=True)
    mv_pa = Property()

    def _get_mv_pa(self):
        return util.dbi(self.sensitivity) * 1e3

    def _set_mv_pa(self, value):
        self.sensitivity = util.db(value * 1e-3)

    @classmethod
    def as_attenuation(cls, vrms=1, **kwargs):
        '''
        Allows levels to be specified in dB attenuation
        '''
        return cls.from_spl(0, vrms, **kwargs)

    @classmethod
    def from_spl(cls, spl, vrms=1, **kwargs):
        '''
        Generates a calibration object based on the recorded SPL

        Parameters
        ----------
        spl : array-like
            List of magnitudes (e.g., speaker output in SPL) for the specified
            RMS voltage.
        vrms : float
            RMS voltage (in Volts)

        Additional kwargs are passed to the class initialization.
        '''
        sensitivity = util.db(vrms)-spl-util.db(20e-6)
        return cls(sensitivity, **kwargs)

    @classmethod
    def from_mv_pa(cls, mv_pa, **kwargs):
        sens = util.db(mv_pa*1e-3)
        return cls(sens, **kwargs)

    def __init__(self, sensitivity, fixed_gain=0, source=None):
        '''
        Parameters
        ----------
        sensitivity : float
            Sensitivity of system in dB(V/Pa).
        '''
        self.sensitivity = sensitivity
        self.fixed_gain = fixed_gain
        self.source = source

    def get_sens(self, frequency):
        return self.sensitivity-self.fixed_gain


class UnityCalibration(FlatCalibration):

    def __init__(self, fixed_gain=0, source=None):
        # This value gives us unity passthrough (because the core methods
        # assume everything is in units of dB(Vrms/Pa)).
        sensitivity = -util.db(20e-6)
        super().__init__(sensitivity, fixed_gain=fixed_gain, source=source)


class InterpCalibration(Calibration):
    '''
    Use when calibration is not flat (i.e., uniform) across frequency.

    Parameters
    ----------
    frequency : array-like, Hz
        Calibrated frequencies (in Hz)
    sensitivity : array-like, dB(V/Pa)
        Sensitivity at calibrated frequency in dB(V/Pa) assuming 1 Vrms and 0 dB
        gain.  If you have sensitivity in V/Pa, just pass it in as
        20*np.log10(sens).
    fixed_gain : float
        Fixed gain of the input or output.  The sensitivity is calculated using
        a gain of 0 dB, so if the input (e.g. a microphone preamp) or output
        (e.g. a speaker amplifier) adds a fixed gain, this needs to be factored
        into the calculation.

        For input calibrations, the gain must be negative (e.g. if the
        microphone amplifier is set to 40 dB gain, then provide -40 as the
        value).
    '''

    frequency = Typed(np.ndarray).tag(metadata=True)
    sensitivity = Typed(np.ndarray).tag(metadata=True)
    fixed_gain = Float(0).tag(metadata=True)
    _interp = Callable()

    def __init__(self, frequency, sensitivity, fixed_gain=0, source=None):
        self.frequency = np.asarray(frequency)
        self.sensitivity = np.asarray(sensitivity)
        self.fixed_gain = fixed_gain
        self._interp = interp1d(frequency, sensitivity, 'linear',
                                bounds_error=False)
        self.source = source

    def get_sens(self, frequency):
        # Since sensitivity is in dB(V/Pa), subtracting fixed_gain from
        # sensitivity will *increase* the sensitivity of the system.
        return self._interp(frequency)-self.fixed_gain


class PointCalibration(Calibration):

    frequency = Typed(np.ndarray).tag(metadata=True)
    sensitivity = Typed(np.ndarray).tag(metadata=True)
    fixed_gain = Float(0).tag(metadata=True)

    def __init__(self, frequency, sensitivity, fixed_gain=0, source=None):
        if np.isscalar(frequency):
            frequency = [frequency]
        if np.isscalar(sensitivity):
            sensitivity = [sensitivity]
        self.frequency = np.array(frequency)
        self.sensitivity = np.array(sensitivity)
        self.fixed_gain = fixed_gain
        self.source = source

    def get_sens(self, frequency):
        if np.iterable(frequency):
            return np.array([self._get_sens(f) for f in frequency])
        else:
            return self._get_sens(frequency)

    def _get_sens(self, frequency):
        try:
            i = np.flatnonzero(np.equal(self.frequency, frequency))[0]
        except IndexError:
            log.debug('Calibrated frequencies are %r', self.frequency)
            m = 'Frequency {} not calibrated'.format(frequency)
            raise CalibrationError(m)
        return self.sensitivity[i]-self.fixed_gain


    @classmethod
    def from_psi_chirp(cls, folder, output_gain=None, **kwargs):
        filename = os.path.join(folder, 'chirp_sensitivity.csv')
        sensitivity = pd.io.parsers.read_csv(filename)
        if output_gain is None:
            output_gain = sensitivity.loc[:, 'hw_ao_chirp_level'].max()
        m = sensitivity['hw_ao_chirp_level'] == output_gain
        mic_freq = sensitivity.loc[m, 'frequency'].values
        mic_sens = sensitivity.loc[m, 'sens'].values
        source = 'psi_chirp', folder, output_gain
        return cls(mic_freq, mic_sens, source=source, **kwargs)


class EPLCalibration(InterpCalibration):

    @classmethod
    def from_epl(cls, filename, **kwargs):
        calibration = pd.io.parsers.read_csv(filename, skiprows=14,
                                             delimiter='\t')
        freq = calibration['Freq(Hz)']
        spl = calibration['Mag(dB)']
        return cls.from_spl(freq, spl, source=filename, **kwargs)


class GolayCalibration(InterpCalibration):

    fs = Float()
    phase = Typed(np.ndarray)

    def __init__(self, frequency, sensitivity, fs=None, phase=None,
                 fixed_gain=0, **kwargs):
        super().__init__(frequency, sensitivity, fixed_gain, **kwargs)
        # fs and phase are required for the IIR stuff
        if fs is not None:
            self.fs = fs
        if phase is not None:
            self.phase = phase

    @staticmethod
    def load_psi_golay(folder, n_bits=None, output_gain=None):
        folder = Path(folder)
        sensitivity = pd.io.parsers.read_csv(folder / 'sensitivity.csv')
        if n_bits is None:
            n_bits = sensitivity['n_bits'].max()
        if output_gain is None:
            m = sensitivity['n_bits'] == n_bits
            output_gain = sensitivity.loc[m, 'output_gain'].max()
        m_n_bits = sensitivity['n_bits'] == n_bits
        m_output_gain = sensitivity['output_gain'] == output_gain
        m = m_n_bits & m_output_gain
        mic_freq = sensitivity.loc[m, 'frequency'].values
        mic_sens = sensitivity.loc[m, 'sens'].values
        mic_phase = sensitivity.loc[m, 'phase'].values
        source = 'psi_golay', folder, n_bits, output_gain
        carray = bcolz.carray(rootdir=folder / 'pt_epoch')
        fs = carray.attrs['fs']
        return {
            'frequency': mic_freq,
            'sensitivity': mic_sens,
            'phase': mic_phase,
            'fs': fs,
        }

    @classmethod
    def from_psi_golay(cls, folder, n_bits=None, output_gain=None, **kwargs):
        folder = Path(folder)
        data = cls.load_psi_golay(folder, n_bits, output_gain)
        data.update(kwargs)
        return cls(source=folder, **data)

    def get_iir(self, fs, fl, fh, truncate=None):
        fs_ratio = self.fs/fs
        if int(fs_ratio) != fs_ratio:
            m = 'Calibration sampling rate, {}, must be an ' \
                'integer multiple of the requested sampling rate'
            raise ValueError(m.format(self.fs))

        n = (len(self.frequency)-1)/fs_ratio + 1
        if int(n) != n:
            m = 'Cannot achieve requested sampling rate ' \
                'TODO: explain why'
            raise ValueError(m)
        n = int(n)

        fc = (fl+fh)/2.0
        freq = self.frequency
        phase = self.phase
        sens = self.sensitivity - (self.get_sens(fc) + self.fixed_gain)
        sens[freq < fl] = 0
        sens[freq >= fh] = 0
        m, b = np.polyfit(freq[freq < fh], phase[freq < fh], 1)
        invphase = 2*np.pi*np.arange(len(freq))*m
        inv_csd = util.dbi(sens)*np.exp(invphase*1j)

        # Need to trim so that the data is resampled accordingly
        if fs_ratio != 1:
            inv_csd = inv_csd[:n]
        iir = np.fft.irfft(inv_csd)

        if truncate is not None:
            n = int(truncate*fs)
            iir = iir[:n]

        return iir


if __name__ == '__main__':
    import doctest
    doctest.testmod()
