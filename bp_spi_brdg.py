#!/usr/bin/env python

"""
the class as similar interface as the Serial class
it translates read and write requests to Bus Pirate read and write SPI requests
"""


import pyBusPirateLite.SPI as bp

#from profilehooks import profile

import threading
import logging


class BpSpiBridgeError(Exception):
    """SPI Bus Pirate bridge error class"""
    pass


class BpSpiBridge(object):
    """SPI Bus Pirate bridge"""
    def __init__(self, port='/dev/bus_pirate', baudrate=bp.SPISpeed._2MHZ, log=None): #pylint: disable=W0212, C0301
        """init the bridge"""
        if not log:
            raise BpSpiBridgeError('no logger provided')
        self.log = log
        self.log.critical('bridge starting')

        # instantiating and configuring the Bus Pirate
        spi = bp.SPI(port, 115200)

        # exit bit bang mode
        spi.resetBP()
        # enter bit bang mode
        if not spi.BBmode():
            self.log.critical('bridge failed to enter in bitbang mode')
            raise BpSpiBridgeError('bridge failed to enter in bitbang mode')
        # enter I2C mode
        if not spi.enter_SPI():
            self.log.critical('bridge failed to enter in SPI mode')
            raise BpSpiBridgeError('bridge failed to enter in SPI mode')
        spi.set_speed(baudrate)

        # configuring SPI:
        #    pin out 3.3V: 1
        #    clock idle low: 0
        #    clock edge idle to active: 0
        #    sample time middle: 0
        spi.cfg_spi(bp.SPICfg.OUT_TYPE)

        # turn on the power supply
        spi.cfg_pins(bp.PinCfg.POWER)

        self.spi = spi
        self.data = ''
        self.mutex = threading.Lock()

        self.log.critical('bridge configured')

    def __del__(self):
        try:
            self.close()
        except: #pylint: disable=W0702
            pass

    def close(self):
        """cleanly stop the Bus Pirate"""
        # turn off the power supply
        self.spi.cfg_pins(0)

        # exit bit bang mode
        self.spi.resetBP()

        self.spi = None

        self.log.critical('bridge stopped')

    def isOpen(self):    #pylint: disable=C0103
        """mimic serial.isOpen()"""
        return self.spi != None

    #@profile
    def _refresh_data(self):
        """get data from SPI"""

        self.mutex.acquire()
        # due to SPI link, if no data are available
        if len(self.data) == 0:
            # read some ahead
            self.spi.CS_Low()
            self.data += self.spi.bulk_trans(16, [0] * 16)
            self.spi.CS_High()

            log = '_refresh_data(): ' \
                + ''.join(['%02x ' % ord(dat) for dat in self.data]) \
                + ' (l = %d)' % len(self.data)
            self.log.debug(log)

        length = len(self.data)
        self.mutex.release()

        return length

    def inWaiting(self):    #pylint: disable=C0103
        """mock-up serial.inWaiting()"""
        return self._refresh_data()

    def read(self, size=1):
        """mock-up serial.read()"""
        self._refresh_data()

        self.mutex.acquire()
        dat = self.data[:size]
        self.data = self.data[size:]
        self.mutex.release()
        return dat

    def write(self, data):
        """mock-up serial.write()"""
        fdata = [ ord(d) for d in data ]

        log = 'write(): ' \
            + ''.join(['%02x ' %d for d in fdata])
        self.log.info(log)

        self.mutex.acquire()
        self.spi.CS_Low()
        # only 16 char max by transfer
        while len(fdata):
            dat = fdata[:16]
            self.log.debug('bulk_trans(%d)' % len(dat))
            self.data += self.spi.bulk_trans(len(dat), dat)
            fdata = fdata[16:]
        self.spi.CS_High()
        self.mutex.release()


if __name__ == '__main__':
	# set a basic logger
    logger = logging.getLogger(__name__)
    handler = logging.FileHandler('spi_bp.log', mode='w')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    brdg = BpSpiBridge(log=logger)
    brdg.write(b'test')
    rd = brdg.read(50)
    print 'res = 0x' + ''.join(['%02x ' % ord(r) for r in rd])
