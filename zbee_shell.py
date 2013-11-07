#!/usr/bin/env python
"""
zbee_shell.py

Yann GOUY

inspired from shell.py in Xbee-python

Provides a simple shell for testing ZBee devices.
"""

import xbee.zigbee
import bp_spi_brdg

import cmd
import logging


class FrameId:  #pylint: disable=R0903
    """simple frame id generator"""
    def __init__(self):
        self._id = 3

    def next(self):
        """return next valid frame id"""
        self._id += 1
        self._id &= 0xff
        if self._id == 0:
            self._id = 1

        return chr(self._id)


class ZBeeShell(cmd.Cmd): #pylint: disable=R0904
    """simple shell for ZigBee interaction"""
    def __init__(self):
        cmd.Cmd.__init__(self)

        self.prompt = "TRoll > "

        # set a basic logger
        self.log = logging.getLogger('zbee_shell')
        handler = logging.FileHandler('zbee_shell.log', mode='w')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

        print('connecting to Zbee through Bus Pirate...')
        self.brdg = bp_spi_brdg.BpSpiBridge(log=self.log)
        self.zbee = xbee.ZigBee(self.brdg, callback=self.callback, \
                callback_extra_param=self)

        self.frame_id = FrameId()

    @staticmethod
    def callback(frame, self):
        """display the received frames"""

		# log hexa value of the frame
        self.log.info( 'read(%d): ' % len(frame.output()) + \
                ''.join(['%02x ' % ord(d) for d in frame.output()])
        )

        # beautify packet before printing
        packet = self.zbee._split_response(frame.data)
        try:
            packet['parameter'] = ord(packet['parameter'])
        except KeyError:
            pass
        except TypeError:
            pass

        rxed = '\b' * 50
        rxed += '\x1b[93m'  # yellow color
        rxed += 'rx -> {'
        rxed += "'id': %r" % packet['id']
        rxed += ", 'status': %r" % packet['status']
        if 'frame_id' in packet:
            rxed += ", \n\t'frame_id': 0x%02x" % ord(packet['frame_id'])
        if 'source_addr_long' in packet:
            rxed += ", \n\t'source_addr_long': 0x"
            conv = ['%02x' % ord(s) for s in packet['source_addr_long']]
            rxed += ''.join(conv)
        if 'source_addr' in packet:
            rxed += ", 'source_addr': 0x"
            conv = ['%02x' % ord(s) for s in packet['source_addr']]
            rxed += ''.join(conv)
        if 'command' in packet:
            rxed += ", \n\t'command': %r" % packet['command']
        if 'parameter' in packet:
            rxed += ", 'parameter: %r" % packet['parameter']

        rxed += '}'
        rxed += '\x1b[0m'   # normal color
        print(rxed)

        self.log.info('%r' % packet)
        self.stdout.write(self.prompt)
        self.stdout.flush()

    def emptyline(self):
        pass

    def do_EOF(self, _): #pylint: disable=C0103
        """ ^d for quit"""
        print
        return self.do_quit(None)

    def do_quit(self, _):
        """quit from the ZBee shell"""
        self.zbee.halt()
        self.brdg.close()
        return 1

    do_q = do_quit

    def do_addr(self, _):
        """display addressing info"""

        # serial number ATSH ATSL
        self.log.info('at SH')
        self.zbee.at(command='SH', frame_id=self.frame_id.next())
        self.log.info('at SL')
        self.zbee.at(command='SL', frame_id=self.frame_id.next())

        # network address ATMY
        self.log.info('at MY')
        self.zbee.at(command='MY', frame_id=self.frame_id.next())

        # node id ATNI
        self.log.info('at NI')
        self.zbee.at(command='NI', frame_id=self.frame_id.next())


    def do_network(self, _):
        """display networking info"""
        # extended PAN id ATID
        self.log.info('at ID')
        self.zbee.at(command='ID', frame_id=self.frame_id.next())

        # operating extended PAN id ATOP
        self.log.info('at OP')
        self.zbee.at(command='OP', frame_id=self.frame_id.next())

        # operating 16-bit PAN id ATOI
        self.log.info('at OI')
        self.zbee.at(command='OI', frame_id=self.frame_id.next())

    def do_rf(self, _):
        """display RF interfacing info"""
        # power level ATPL
        self.log.info('at PL')
        self.zbee.at(command='PL', frame_id=self.frame_id.next())

        # received signal strength ATDB
        self.log.info('at DB')
        self.zbee.at(command='DB', frame_id=self.frame_id.next())

        # peak power ATPP
        self.log.info('at PP')
        self.zbee.at(command='PP', frame_id=self.frame_id.next())

    def do_diag(self, _):
        """display diagnostic info"""
        # association indicator ATAI
        self.log.info('at AI')
        self.zbee.at(command='AI', frame_id=self.frame_id.next())

        # firmware version ATVR
        self.log.info('at VR')
        self.zbee.at(command='VR', frame_id=self.frame_id.next())

        # hardware version ATHV
        self.log.info('at HV')
        self.zbee.at(command='HV', frame_id=self.frame_id.next())

        # supply voltage AT%V [mV]
        self.log.info('at %V')
        self.zbee.at(command='%V', frame_id=self.frame_id.next())

        # module temperature ATTP [C]
        self.log.info('at TP')
        self.zbee.at(command='TP', frame_id=self.frame_id.next())

    def help_tx(self):   #pylint: disable=R0201
        """provide an example for tx command format"""
        print('tx cmd {params in dict}')
        print('for example:')
        print("tx remote_at {"
            + "'dest_addr_long': "
            + "'\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00', "
            + "'dest_addr': '\\xff\\xfe', "
            + "'options': '\\x00', "
            + "'command': "
            + "'CE', 'parameter': ''}")

    def do_tx(self, data):
        """send an raw data"""
        cmnd = data.split(' ', 1)
        try:
            frame = eval(cmnd[1])
        except SyntaxError, err:
            print('SyntaxError: %r' % err)
            return

        frame['frame_id'] = self.frame_id.next()
        self.log.info('%r' % frame)
        self.zbee.send(cmnd[0], **frame)

    def do_at(self, cmnd):
        """
        send an AT command with the format
        <command> <parameter>
        frame id will be automatically inserted
        """
        self.log.info('at %r' % cmnd)
        cmnd = cmnd.split()
        try:
            param = ''
            for i in range(0, len(cmnd[1]), 2):
                _ch = int(cmnd[1][i:i + 2], 16)
                param += chr(_ch)
        except IndexError:
            param = None

        try:
            self.zbee.at(
                command=cmnd[0],
                frame_id=self.frame_id.next(),
                parameter=param
            )

        except KeyError, exc:
            print exc
            return
        except ValueError, exc:
            print exc
            return

if __name__ == '__main__':
    try:
        ZBeeShell().cmdloop()
    except KeyboardInterrupt:
        pass
