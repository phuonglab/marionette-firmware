#!/usr/bin/env python
# file: DUT.py


"""
Sun 13 July 2014 11:55:14 (PDT)
TODO: Python exception handling with the serial port is not great.
    - minicom might be open and accessing the port at the same time but exceptions aren't
        consistently raised in serial.read/serial.readline

NOTE: ctrl-c quitting-may take more than one ctrl-c for program to exit
"""


""" 
This tool is used to manipulate a D_evice U_nder T_est

Example: 

Connect a device to the Default_Port.
~/.../library/python/devtest (adc*) > ./DUT.py 

"""

import sys
import threading
import serial
from time import sleep
import utils as u

DUT_WAITTIME     = 0.200
Default_Baudrate = 115200
Default_Timeout  = 2
Default_Port     = "/dev/ttyACM0"

class DUTSerial():
    def __init__(self, port=Default_Port, baud=Default_Baudrate, timeout=Default_Timeout):
        self.serial_port    = port
        self.baud           = baud
        self.timeout        = timeout
        self.isOpen         = False
        return

    def start(self):
        if not self.isOpen:
            self.ser          = serial.Serial()
            self.ser.baudrate = self.baud
            self.ser.port     = self.serial_port   # readline and readlines will block forever if no timeout
            self.ser.timeout  = self.timeout

            """
             pyserial can't always grab the device. Change something trivial
             Then it works. 
            """
            self.ser.parity   = serial.PARITY_ODD
            try:
                self.ser.open()
            except serial.SerialException  as e:
                u.error("Error opening serial port: " + str(e))
                sys.exit()
            self.ser.close()
            self.ser.parity   = serial.PARITY_NONE
            self.ser.open()
            if self.ser.isOpen() == True:
                s = "opened port {}\n".format(self.serial_port)
                u.info(s)
                self.isOpen       = True
                self.alive        = True
                self._start_reader()
                self.tx_thread = threading.Thread(target=self.writer)
                self.tx_thread.setDaemon(True)
                self.tx_thread.start()

            else:
                print("Failed to open port: ", self.serial_port)
                self.isOpen       = False
                self.alive        = False
        return

    def join(self, tx_only=False):
        self.tx_thread.join()
        if not tx_only:
            self._reader_alive = False
            self.rx_thread.join()

    def _start_reader(self):
        """Start reader thread"""
        self._reader_alive = True
        self.rx_thread = threading.Thread(target=self.reader)
        self.rx_thread.setDaemon(True)
        self.rx_thread.start()

    def reader(self):
        try:
            while self.alive and self._reader_alive:
                line = self.ser.readline()    # don't forget timeout setting
                if len(line) > 0:
                    print(line.decode('ascii'), end="", flush=True)
                else:
                    pass
            print("")
            sys.stdout.flush()
        except serial.SerialException  as e:
            self.alive = False
            u.error("Error reading serial port: " + str(e))
            sys.exit()

    def teststr(self, string):
        u.info("sending\t->"+string)
        self.write(string)
        sleep(DUT_WAITTIME)

    def testctl(self):
        u.info("Testing help command")
        self.teststr("help\r\n")
        u.info("Testing the empty string.")
        self.teststr("")
        u.info("Testing cr lf.")
        self.teststr("\r\n")
        u.info("Testing ctl-d (will restart shell)")
        self.teststr('\x04')   # ctrl-d in ascii will cause logout event, and marionette terminal will restart
        sleep(4.5)
        self.write("\n\r")

    def test_gpio(self):
        u.info("Set an output to floating.")
        self.teststr("gpio:configure:porth:pin2:output:floating\r\n")
        u.info("Test extra spaces in command.")
        self.teststr(" gpio : \tconfigure :p   orth:p\tin2:output:floa\t  \tt\t i n    g\r\n")
        u.info("Test bad command (should produce error)")
        self.teststr(" gpio \r\n")
        u.info("Test incomplete command (should produce error)")
        self.teststr("gpio:configure\r\n")
        u.info("Test configure command")
        self.teststr("gpio:configure:porti:pin10:output:floating\r\n")
        self.teststr("gpio:configure:porth:pin2:output:floating\r\n")
        response = input("Pause. Press <enter>")
        u.info("Test set command")
        self.teststr("gpio:set:porth:pin2\r\n")
        self.teststr("gpio:set:porti:pin10\r\n")
        u.info("Test get command")
        self.teststr("gpio:get:porth:pin2\r\n")
        u.info("Test clear command")
        self.teststr("gpio:clear:porth:pin2\r\n")
        u.info("Test get command")
        self.teststr("gpio:get:porth:pin2\r\n")
        self.teststr("gpio:get:porti:pin10\r\n")
        response = input("Pause. Press <enter>")
        u.info("Test set command")
        self.teststr("gpio:set:porth:pin2\r\n")
        u.info("Test resetpins command")
        self.teststr("resetpins\r\n")
        u.info("Test get command")
        self.teststr("gpio:get:porth:pin2\r\n")
 
    def test_adc(self):
        u.info("Test one shot with default profile.")
        self.teststr("adc:conf_adc1:profile:default\r\n")
        self.teststr("adc:conf_adc1:oneshot\r\n")
        self.teststr("adc:start\r\n")
        self.teststr("adc:start\r\n")
        response = input("Test continuous with default profile for 1.5 seconds. Press <enter>")
        self.teststr("adc:conf_adc1:profile:default\r\n")
        self.teststr("adc:conf_adc1:continuous\r\n")
        self.teststr("adc:start\r\n")
        sleep(1.5)
        self.teststr("adc:stop\r\n")
        sleep(1.0)
        response = input("Test one shot with demo profile. Press <enter>")
        self.teststr("adc:conf_adc1:profile:demo\r\n")
        self.teststr("adc:conf_adc1:oneshot\r\n")
        self.teststr("adc:start\r\n")
        self.teststr("adc:start\r\n")
        response = input("Test continuous with demo profile for 1 second. Press <enter>")
        self.teststr("adc:conf_adc1:continuous\r\n")
        self.teststr("adc:start\r\n")
        sleep(1.0)
        self.teststr("adc:stop\r\n")
        sleep(1.0)
        response = input("Test one shot with pa profile. Press <enter>")
        self.teststr("adc:conf_adc1:profile:pa\r\n")
        self.teststr("adc:conf_adc1:oneshot\r\n")
        self.teststr("adc:start\r\n")
        self.teststr("adc:start\r\n")
        response = input("Test continuous with pa profile for 1 second. Press <enter>")
        self.teststr("adc:conf_adc1:continuous\r\n")
        self.teststr("adc:start\r\n")
        sleep(1.0)
        self.teststr("adc:stop\r\n")
        sleep(1.0)
        response = input("Set the reference voltage to 2.5 volts. Press <enter>")
        self.teststr("adc:conf_adc1:vref_mv(2500)\r\n")
        response = input("Test one shot with pa profile. Press <enter>")
        self.teststr("adc:conf_adc1:oneshot\r\n")
        response = input("Pause. Press <enter>")
        self.teststr("adc:start\r\n")
        sleep(0.5)
        response = input("Reset the adc. Press <enter>")
        self.teststr("adc:conf_adc1:reset\r\n")
        u.info("Confirm reset to default profile and one shot.")
        self.teststr("adc:start\r\n")
 
    def writer(self):
        try:
            if self.alive:
                reponse = input("\r\nStart the Demo. Please press <enter>")
                reponse = input("\r\nReady to test control. Please press <enter>")
                self.testctl()
                self.write("\r\n")
                sleep(2.5)
                reponse = input("\r\nTurn off the prompt. Please press <enter>")
                self.teststr("+noprompt\r\n")
                sleep(0.5)
                self.write("resetpins\r\n")
                sleep(0.5)
                reponse = input("\r\nReady to test gpio. Please press <enter>")
                self.test_gpio()
                self.write("resetpins\r\n")
                self.teststr("+noprompt\r\n")
                reponse = input("\r\nReady to test the adc. Please press <enter>")
                self.test_adc()
                reponse = input("\r\nReturn the prompt. Please press <enter>")
                self.teststr("+prompt\r\n")

        except KeyboardInterrupt:
            self.alive = False
            DUT.close()
            u.info("\r\nQuitting-keyboard interrupt.")

        except:
            self.alive = False
            DUT.close()
            raise



    def write(self, s):
        bytes = str.encode(s)    # Because python and strings
        numbytes = self.ser.write(bytes) 
        return numbytes

    def close(self):
        self.join(True)
        self.join()
        self.alive  = False
        if self.ser.isOpen() == True:
            self.ser.close()
            self.isOpen = False
            s="closed port: {}\n".format(self.serial_port)
            u.info(s)
        return

if __name__ == "__main__":
    try:
        # optparse here eventually... baud port filename quiet
        serial_port    = Default_Port
#        baud           = 460800
        baud           = 115200
        timeout        = Default_Timeout

        DUT       = DUTSerial(serial_port, baud, timeout)
        DUT.start()

        DUT.close()
        print("Bye.")

    except serial.SerialException:
        DUT.close()
        u.error("Serial Exception: " + str(e))
    except KeyboardInterrupt:
        DUT.close()
        u.info("\r\nQuitting-keyboard interrupt.")

# Attic

#    ser = DUTSerial(baud=baud, timeout=timeout)   # example of default args to init
#      from time import sleep
#                self.ser.setDTR(True)
#                self.ser.setRTS(True)
#                sleep(0.100)
#      self.ser.xonxoff  = 1
#      self.ser.rtscts   = 0
#      self.ser.dsrdtr   = 0

