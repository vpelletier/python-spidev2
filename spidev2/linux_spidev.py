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
Low-level ctypes translation of linux/spi/spi{,dev}.h

You should not have to import this file outside this package.
"""

import ctypes
import enum
from ioctl_opt import IOW, IOR

# pylint: disable=invalid-name

class SPIMode32(enum.IntFlag):
    """
    SPI bus mode flags

    See linux/spi/spi.h
    """
    SPI_CPHA        = 1 << 0 # clock phase
    SPI_CPOL        = 1 << 1 # clock polarity

    SPI_MODE_0      = 0        | 0        # (original MicroWire)
    SPI_MODE_1      = 0        | SPI_CPHA
    SPI_MODE_2      = SPI_CPOL | 0
    SPI_MODE_3      = SPI_CPOL | SPI_CPHA

    SPI_CS_HIGH     = 1 << 2  # chipselect active high?
    SPI_LSB_FIRST   = 1 << 3  # per-word bits-on-wire
    SPI_3WIRE       = 1 << 4  # SI/SO signals shared
    SPI_LOOP        = 1 << 5  # loopback mode
    SPI_NO_CS       = 1 << 6  # 1 dev/bus, no chipselect
    SPI_READY       = 1 << 7  # slave pulls low to pause
    SPI_TX_DUAL     = 1 << 8  # transmit with 2 wires
    SPI_TX_QUAD     = 1 << 9  # transmit with 4 wires
    SPI_RX_DUAL     = 1 << 10 # receive with 2 wires
    SPI_RX_QUAD     = 1 << 11 # receive with 4 wires
    SPI_CS_WORD     = 1 << 12 # toggle cs after each word
    SPI_TX_OCTAL    = 1 << 13 # transmit with 8 wires
    SPI_RX_OCTAL    = 1 << 14 # receive with 8 wires
    SPI_3WIRE_HIZ   = 1 << 15 # high impedance turnaround

SPI_MODE_X_MASK = SPIMode32.SPI_CPOL | SPIMode32.SPI_CPHA
SPI_MODE_USER_MASK = (1 << 16) - 1

_SPI_IOC_MAGIC = ord(b'k')

# pylint: disable=too-many-instance-attributes,too-few-public-methods
class spi_ioc_transfer(ctypes.Structure):
    """
    spidev transfer structure

    See linux/spi/spidev.h
    """
    _fields_ = (
        ('tx_buf', ctypes.c_uint64),
        ('rx_buf', ctypes.c_uint64),

        ('len', ctypes.c_uint32),
        ('speed_hz', ctypes.c_uint32),

        ('delay_usecs', ctypes.c_uint16),
        ('bits_per_word', ctypes.c_uint8),
        ('cs_change', ctypes.c_uint8),
        ('tx_nbits', ctypes.c_uint8),
        ('rx_nbits', ctypes.c_uint8),
        ('word_delay_usecs', ctypes.c_uint8),
        ('pad', ctypes.c_uint8),
    )
# pylint: enable=too-many-instance-attributes,too-few-public-methods

def SPI_IOC_MESSAGE(transfer_count):
    """
    spidev ioctl supporting multiple transfers in one ioctl syscall.
    """
    return IOW(_SPI_IOC_MAGIC, 0, spi_ioc_transfer * transfer_count)

# Read / Write of SPI mode (SPI_MODE_0..SPI_MODE_3) (limited to 8 bits)
SPI_IOC_RD_MODE = IOR(_SPI_IOC_MAGIC, 1, ctypes.c_uint8)
SPI_IOC_WR_MODE = IOW(_SPI_IOC_MAGIC, 1, ctypes.c_uint8)

# Read / Write SPI bit justification
SPI_IOC_RD_LSB_FIRST = IOR(_SPI_IOC_MAGIC, 2, ctypes.c_uint8)
SPI_IOC_WR_LSB_FIRST = IOW(_SPI_IOC_MAGIC, 2, ctypes.c_uint8)

# Read / Write SPI device word length (1..N)
SPI_IOC_RD_BITS_PER_WORD = IOR(_SPI_IOC_MAGIC, 3, ctypes.c_uint8)
SPI_IOC_WR_BITS_PER_WORD = IOW(_SPI_IOC_MAGIC, 3, ctypes.c_uint8)

# Read / Write SPI device default max speed hz
SPI_IOC_RD_MAX_SPEED_HZ = IOR(_SPI_IOC_MAGIC, 4, ctypes.c_uint32)
SPI_IOC_WR_MAX_SPEED_HZ = IOW(_SPI_IOC_MAGIC, 4, ctypes.c_uint32)

# Read / Write of the SPI mode field
SPI_IOC_RD_MODE32 = IOR(_SPI_IOC_MAGIC, 5, ctypes.c_uint32)
SPI_IOC_WR_MODE32 = IOW(_SPI_IOC_MAGIC, 5, ctypes.c_uint32)
