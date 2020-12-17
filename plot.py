#!/usr/bin/env python3

import argparse
import logging
import pathlib
import typing

import numpy
import scipy.io.wavfile
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
    argparser = argparse.ArgumentParser()
    argparser.add_argument("recording_paths", type=pathlib.Path, nargs="+")
    args = argparser.parse_args()
    _LOGGER.debug("args=%r", args)
    for recording_path in args.recording_paths:
        pyplot.plot(read_recording(recording_path), label=recording_path.name)
    pyplot.legend()
    pyplot.show()


if __name__ == "__main__":
    _main()
