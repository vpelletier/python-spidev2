Pure-python interface to Linux spidev.

Features
--------

- Pythonic API
- Pure python module: no compilation needed, not limited to CPython.

Requirements
------------

- Linux >=3.14 for ``SPI_IOC_{RD,WR}_MODE32`` ioctls
- python3 >=3.7 (cpython, pypy, ...)

Examples
--------

Warning: this example is **not** meant to be executed as-is. Depending on what
is connected to the SPI bus used here (which is entirely board-dependent),
this could cause all sort of problems, including permanent hardware damage.

This is only to be taken as a quick overview of this module's API.

.. code:: python

    from spidev2 import SPIBus, SPITransferList, SPIMode32

    with SPIBus(
        '/dev/spidev0.0',
        'w+b',
        bits_per_word=8,
        speed_hz=16_000_000,
        spi_mode=(
            SPIMode32.SPI_MODE_0 |
            SPIMode32.SPI_TX_OCTAL |
            SPIMode32.SPI_RX_OCTAL
        ),
    ) as spi:
        # Simple single-transfer full-duplex usage. Low performance: a reception
        # buffer is allocated on every call, and as the tranmission buffer is
        # immutable, it will be copied
        received = spi.transfer(
            tx_buf=b'\x12\x34\x00\x00',
            speed_hz=1_000_000,
        )[2:]

        # The same transfer, with reusable buffers for better performance
        # (the kernel will still copy memory both ways).
        spi_tx_buffer = bytearray(4)
        spi_rx_buffer = bytearray(len(spi_tx_buffer))
        # Initialise the tx buffer for the upcomming transfer
        spi_tx_buffer[0:2] = b'\x12\x34'
        spi.transfer(
            tx_buf=spi_tx_buffer,
            rx_buf=spi_rx_buffer,
            speed_hz=1_000_000,
        )
        received = spi_rx_buffer[2:]

        # It is also possible to use the same transfer both ways:
        spi_buffer = bytearray(4)
        spi_buffer[0:2] = b'\x12\x34'
        spi.transfer(
            tx_buf=spi_buffer,
            rx_buf=spi_buffer,
            speed_hz=1_000_000,
        )
        received = spi_buffer[2:]

        # Multi-transfer usage. Reduces the number of syscalls, reduces the
        # need to slice buffers to access received values (reducing the
        # number of memory copy operations) and allows transfer structure reuse
        # (reducing memory allocation operations).
        spi_tx_buffer = bytearray(b'\x12\x34')
        received = bytearray(2)
        transfer_list = SPITransgerList((
            {
                'tx_buf': spi_tx_buffer,
                'speed_hz': 1_000_000,
            },
            {
                'rx_buf': received,
                'speed_hz': 1_000_000,
            },
        ))
        spi.submitTransferList(transfer_list)

        # Half-duplex usage, chip-select being released between calls.
        # Per-transfer options are not available, so the bus must be
        # reconfigured if its current configuration is not suitable.
        spi.speed_hz = 1_000_000
        spi.write(b'\x12\x34')
        spi.read(2)
