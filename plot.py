#!/usr/bin/env python3

import argparse
import itertools
import logging
import pathlib
import typing

import numpy
import scipy.io.wavfile
import scipy.ndimage
from matplotlib import pyplot

_LOGGER = logging.getLogger(__name__)

# https://git.hammerle.me/fphammerle/config-ipython/src/3dc22bb705f2c18179413a682f73ae95148634fe/profile_default/startup/init.py#L6
def trim_where(
    # https://docs.python.org/3.8/library/collections.abc.html#collections-abstract-base-classes
    sequence: typing.Sequence,
    condition: typing.Sequence[bool],
) -> typing.Sequence:
    start = 0
    for item_condition in condition:
        if item_condition:
            start += 1
        else:
            break
    stop = len(sequence)
    assert stop == len(condition)
    for item_condition in condition[::-1]:
        if item_condition:
            stop -= 1
        else:
            break
    return sequence[start:stop]


# https://git.hammerle.me/fphammerle/config-ipython/src/3dc22bb705f2c18179413a682f73ae95148634fe/profile_default/startup/init.py#L27
def wavfile_read_mono(path):
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.wavfile.read.html
    rate, data = scipy.io.wavfile.read(path)
    data_first_channel = data[:, 0]
    for channel_index in range(1, data.shape[1]):
        assert (data_first_channel == data[:, channel_index]).all()
    return rate, data_first_channel


def read_recording(path: pathlib.Path) -> numpy.ndarray:
    rate, data = wavfile_read_mono(path)
    assert rate == 48000
    return trim_where(sequence=data, condition=data < 1000)


def _main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s:%(funcName)s:%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
    argparser = argparse.ArgumentParser()
    argparser.add_argument("recording_paths", type=pathlib.Path, nargs="+")
    argparser.add_argument("--plot-signal", action="store_true")
    argparser.add_argument("--plot-digitalized-signal", action="store_true")
    args = argparser.parse_args()
    _LOGGER.debug("args=%r", args)
    bit_lengths = {False: [], True: []}
    for recording_path in args.recording_paths:
        signal = read_recording(recording_path)
        if args.plot_signal:
            pyplot.plot(signal, label=recording_path.name)
        threshold = (signal.min() + signal.max()) / 2
        digitalized_signal = signal > threshold
        if args.plot_digitalized_signal:
            pyplot.plot(
                digitalized_signal * signal.max() / 2, label=recording_path.name
            )
        signal_bit_lengths = {False: [], True: []}
        for group_index, (bit, signal_group_iter) in enumerate(
            itertools.groupby(digitalized_signal)
        ):
            signal_group_length = sum(1 for _ in signal_group_iter)
            if group_index < 31:  # preamble
                if group_index % 2 == 1:
                    assert 16 <= signal_group_length <= 20, signal_group_length
                elif group_index != 0:
                    assert 375 <= signal_group_length <= 422, signal_group_length
            else:
                signal_bit_lengths[bit].append(signal_group_length)
                assert not bit or signal_group_length < 30, signal_group_length
        assert signal_bit_lengths[False][-1] < 6, signal_bit_lengths[False][-1]
        for bit in bit_lengths.keys():
            bit_lengths[bit].extend(signal_bit_lengths[bit][: None if bit else -1])
        print(recording_path, signal_bit_lengths[False])
    if args.plot_signal or args.plot_digitalized_signal:
        pyplot.legend()
        pyplot.figure()
    pyplot.hist(bit_lengths[True], bins=10)
    pyplot.figure()
    pyplot.hist(bit_lengths[False], bins=300)
    pyplot.show()


if __name__ == "__main__":
    _main()
