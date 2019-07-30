from collections import deque
from copy import copy

import pytest
import enaml
import numpy as np

with enaml.imports():
    from psi.controller.calibration import FlatCalibration
    from psi.controller.queue import FIFOSignalQueue
    from psi.token.primitives import Cos2EnvelopeFactory, ToneFactory


@pytest.fixture
def tone1():
    # fs, level, frequency, phase, polarity, calibration
    calibration = FlatCalibration.as_attenuation()
    return ToneFactory(100e3, 0, 5, 0, 1, calibration)


@pytest.fixture
def tone2():
    calibration = FlatCalibration.as_attenuation()
    return ToneFactory(100e3, 0, 10, 0, 1, calibration)


@pytest.fixture
def queue(tone1, tone2):
    # Note that filter delay doesn't actually affect the samples generated by
    # the queue. Instead, it adjusts the start time of the tone burst that's
    # reported.
    queue = FIFOSignalQueue()
    queue.set_fs(100e3)
    queue.set_t0(0)
    queue.append(copy(tone1), 1)
    queue.append(copy(tone2), 1)
    return queue


@pytest.fixture()
def tone_pip():
    calibration = FlatCalibration.as_attenuation()
    tone = ToneFactory(100e3, 0, 250, 0, 1, calibration)
    envelope = Cos2EnvelopeFactory(100e3, 0, 0.5e-3, 5e-3, tone)
    return envelope


def test_queue_uploaded_order(tone_pip):
    queue = FIFOSignalQueue()
    queue.append(tone_pip, 500)
    queue.set_fs(100e3)
    queue.set_t0(0)
    queue.pop_buffer(200e3)

    times = np.array([u['t0'] for u in queue.uploaded])
    assert np.all(np.diff(times) > 0)


def test_queue(queue, tone1, tone2):
    '''
    Test ability to work with continuous tones and move to next
    '''
    conn = deque()
    queue.connect(conn.append)

    assert queue.get_max_duration() is np.inf

    s1 = queue.pop_buffer(100e3)[0]
    gs1 = tone1.next(100e3)
    assert np.allclose(s1, gs1)

    s1 = queue.pop_buffer(100e3)[0]
    gs1 = tone1.next(100e3)
    assert np.allclose(s1, gs1)

    queue.next_trial()

    s2 = queue.pop_buffer(100e3)[0]
    gs2 = tone2.next(100e3)
    assert np.allclose(s2, gs2)

    s2 = queue.pop_buffer(100e3)[0]
    gs2 = tone2.next(100e3)
    assert np.allclose(s2, gs2)

    assert len(conn) == 2
    # Set resolution to a fraction of a sample
    assert conn.popleft()[0]['t0'] == pytest.approx(0, abs=0.1/100e3)
    assert conn.popleft()[0]['t0'] == pytest.approx(2, abs=0.1/100e3)
