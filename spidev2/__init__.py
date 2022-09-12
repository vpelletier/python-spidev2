# -*- coding: utf-8 -*-
# Copyright (C) 2022  Vincent Pelletier <plr.vincent@gmail.com>
#
# This file is part of python-spidev2.
# python-spidev2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-spidev2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-spidev2.  If not, see <http://www.gnu.org/licenses/>.

"""
A pure-pyton gpio implemtation using spidev chardev.
"""

import ctypes
import errno
from fcntl import ioctl
import io
from .linux_spidev import (
    spi_ioc_transfer,
    SPIMode32,
    SPI_MODE_X_MASK,
    SPI_MODE_USER_MASK,
    SPI_IOC_MESSAGE,
    SPI_IOC_RD_LSB_FIRST,
    SPI_IOC_WR_LSB_FIRST,
    SPI_IOC_RD_BITS_PER_WORD,
    SPI_IOC_WR_BITS_PER_WORD,
    SPI_IOC_RD_MAX_SPEED_HZ,
    SPI_IOC_WR_MAX_SPEED_HZ,
    SPI_IOC_RD_MODE32,
    SPI_IOC_WR_MODE32,
)
from . import _version
__version__ = _version.get_versions()['version']

# Note: only listing globals which actually make sense to use outside of this
# package.
__all__ = (
    "SPIMode32", "SPI_MODE_X_MASK", "SPI_MODE_USER_MASK", "SPITransfer",
    "SPITransferList", "SPIBus",
)

_SPI_IOC_MESSAGE_1 = SPI_IOC_MESSAGE(1)

class SPITransfer:
    """
    A bidirectional SPI transfer block.
    """
    def __init__( # pylint: disable=too-many-arguments
        self,
        tx_buf=None,
        rx_buf=None,
        speed_hz=0,
        bits_per_word=0,
        delay_usecs=0,
        cs_change=False,
        tx_nbits=0,
        rx_nbits=0,
        word_delay_usecs=0,
        transfer=None,
    ):
        """
        tx_buf (None or bytes or buffer)
            Data to send over the SPI bus.
            If it is a buffer object (ex: memoryview), its content may be
            modified before resubmitting the transfer, allowing to reuse
            SPITransfer instances.
        rx_buf (None or buffer)
            Data received over the SPI bus.
        delay_usecs (int, 0 to 65535)
            How long to keep CS deasserted after this transfer.
            cs_change must be true and there must be a transfer submitted after
            this one as part of a single full-duplex operation.
        cs_change (bool)
            Whether chip-select signal should be released after this transfer.
            Note: on the last transfer of a sequence, this has the opposite
            effect: CS is kept asserted.
        word_delay_usecs (int, 0 to 255)
            If supported by the SPI controller, how long to wait between
            consecutive words in the current transfer.
        speed_hz (int)
        bits_per_word (int)
        tx_nbits (1, 2, 4)
        rx_nbits (1, 2, 4)
            If non-zero, override the current bus' setting for this transfer.
            {r,t}x_nbits overrides (single)/SPI_{R,T}X_DUAL/SPI_{R,T}X_QUAD.
        transfer (spi_ioc_transfer)
            For SPITransferList use only.

        At least one of tx_buf and rx_buf must be non-None.
        Both tx_buf and rx_buf may reference the same memory.
        """
        if tx_buf is None:
            tx_buf_address = 0
        else:
            length = len(tx_buf)
            try:
                # Only get the first char, this will only be used to get a
                # pointer to tx_buf's first byte.
                tx_buf_raw = ctypes.c_char.from_buffer(tx_buf)
            except TypeError:
                # Slow path: copy tx_buf, to tolerate caller providing an
                # immutable/non-buffer-protocol object.
                self._tx_buf_raw = tx_buf_raw = ctypes.create_string_buffer(
                    tx_buf,
                )
            tx_buf_address = ctypes.addressof(tx_buf_raw)
        if rx_buf is None:
            rx_buf_address = 0
            if tx_buf is None:
                raise ValueError("neither tx_buf nor rx_buf was provided")
        else:
            # rx_buf *must* be mutable and ctypes-compatible. This will raise if
            # it is not.
            rx_buf_address = ctypes.addressof(ctypes.c_char.from_buffer(rx_buf))
            if tx_buf is None:
                length = len(rx_buf)
            else:
                if len(rx_buf) != length:
                    raise ValueError('mismatched lengths')
        self._rx_buf = rx_buf
        self._tx_buf = tx_buf
        if transfer is None:
            transfer = spi_ioc_transfer()
        self._transfer = transfer
        transfer.tx_buf = tx_buf_address
        transfer.rx_buf = rx_buf_address
        transfer.len = length
        transfer.speed_hz = speed_hz
        transfer.bits_per_word = bits_per_word
        transfer.delay_usecs = delay_usecs
        transfer.cs_change = cs_change
        transfer.tx_nbits = tx_nbits
        transfer.rx_nbits = rx_nbits
        transfer.word_delay_usecs = word_delay_usecs

    @property
    def tx_buf(self):
        """
        tx_buf provided to the constructor
        """
        return self._tx_buf

    @property
    def rx_buf(self):
        """
        rx_buf provided to the constructor, or the bytearray created by the
        constructor
        """
        return self._rx_buf

    @property
    def transfer(self):
        """
        For SPIBus use only.
        """
        return self._transfer

class SPITransferList:
    """
    A list of bidirectional SPI transfer blocks.
    """
    def __init__(self, kw_list):
        """
        kw_list (list of dicts)
            Keyword arguments for the initialisation of contained SPITransfer
            objects.
        """
        self._length = length = len(kw_list)
        self._transfer_list = (spi_ioc_transfer * length)()
        self._spi_transfer_list = spi_transfer_list = []
        for transfer, transfer_kw in zip(self._transfer_list, kw_list):
            spi_transfer_list.append(SPITransfer(
                transfer=transfer,
                **transfer_kw
            ))
        self._ioctl_request = SPI_IOC_MESSAGE(length)

    def __len__(self):
        """
        How many SPITransfers there are in this list.
        """
        return self._length

    def __getitem__(self, index):
        """
        Retrieves a SPITransfer.
        """
        return self._spi_transfer_list[index]

    def __iter__(self):
        """
        Iterates over contained SPITransfers.
        """
        return iter(self._spi_transfer_list)

    @property
    def ioctl_args(self):
        """
        For SPIBus use only.
        """
        return (self._ioctl_request, self._transfer_list)

class SPIBus(io.FileIO):
    """
    Wrapper for the /dev/spidev*.* device class.
    Implements spidev ioctl calls in a pythonic way.

    See transfer/submitTransferList for full-duplex and/or chained transfers
    (ex: to control how/when the chip-select signal is released).
    Regular read/write (and derivatives, like readinto) methods are available
    for half-duplex transfers.
    """
    def __init__(
        self,
        *args,
        bits_per_word=None,
        speed_hz=None,
        spi_mode=None,
        **kw
    ):
        """
        bits_per_word (None, int)
            If not None, number of bits per SPI word to immediately set.
            Transfers must be of a whole number of round-up-to-power-of-two
            bytes based on this value (ex: 20 bits requires transfers of
            N*4 bytes)
        speed_hz (None, int)
            If not None, bus default clock frequency to immediately set.
        spi_mode (None, SPIMode32 flags)
            If not None, bus mode flags to immediately set.
        """
        super().__init__(*args, **kw)
        if bits_per_word is not None:
            self.bits_per_word = bits_per_word
        if speed_hz is not None:
            self.speed_hz = speed_hz
        if spi_mode is not None:
            self.spi_mode = spi_mode

    def _ioctl(self, request, arg=0):
        if ioctl(self.fileno(), request, arg) == -1:
            raise OSError

    def seekable(self):
        """
        Chardevs are not seekable.
        """
        return False

    def seek(self, pos, whence=0):
        """
        Always raises OSError.
        """
        raise OSError(errno.ENOTSUP)

    def tell(self):
        """
        Always raises OSError.
        """
        raise OSError(errno.ENOTSUP)

    def truncate(self, size=None):
        """
        Always raises OSError.
        """
        raise OSError(errno.ENOTSUP)

    @property
    def bits_per_word(self):
        """
        Current bus setting.
        """
        result = ctypes.c_uint8()
        self._ioctl(SPI_IOC_RD_BITS_PER_WORD, result)
        return result.value

    @bits_per_word.setter
    def bits_per_word(self, value):
        self._ioctl(SPI_IOC_WR_BITS_PER_WORD, ctypes.c_uint8(value))

    @property
    def speed_hz(self):
        """
        Current bus setting.
        """
        result = ctypes.c_uint32()
        self._ioctl(SPI_IOC_RD_MAX_SPEED_HZ, result)
        return result.value

    @speed_hz.setter
    def speed_hz(self, value):
        self._ioctl(SPI_IOC_WR_MAX_SPEED_HZ, ctypes.c_uint32(value))

    @property
    def spi_mode(self):
        """
        Current bus setting.
        """
        result = ctypes.c_uint8()
        self._ioctl(SPI_IOC_RD_MODE32, result)
        return result.value

    @spi_mode.setter
    def spi_mode(self, value):
        self._ioctl(SPI_IOC_WR_MODE32, ctypes.c_uint32(value))

    def submitTransferList(self, transfer_list):
        """
        transfer_list (SPITransferList)

        Submits and executes a list of SPI transfers in one syscall.

        Returns an iterator over individual transfers' rx_buf.
        """
        self._ioctl(*transfer_list.ioctl_args)
        return (x.rx_transfer for x in transfer_list)

    def transfer(self, *args, **kw):
        """
        Shorthand for submitting a single, non-reusable bidirectional transfer.

        Arguments: see SPITransfer.__init__

        Returns the transfer's rx_buf.
        """
        transfer = SPITransfer(*args, **kw)
        self._ioctl(_SPI_IOC_MESSAGE_1, transfer.transfer)
        return transfer.rx_buf
