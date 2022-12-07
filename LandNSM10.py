import binascii
import serial as sr
import struct
import time
import os


#
# Documentation: "Serial protocol documentation of the Luigs & Neumann
#                 manipulator control systems SM-10"
#
# Interface description V1.0
#
#
# Based on LuigsAndNeumannSM5 by mgraupe:
# https://github.com/mgraupe/LuigsAndNeumannSM5
#
#
# Written by David Nguyen (07/12/2022):
# 
#

# Serial protocol properties
PORT = 'COM3'
BAUDRATE = 115200
BYTESIZE = sr.EIGHTBITS
PARITY = sr.PARITY_NONE
STOPBITS = sr.STOPBITS_ONE
CONNECTION_TIMEOUT = 0.1 # [seconds]

# Time to sleep after sending a serial command
CMD_SLEEP = 0.1 # [seconds]

# Syntax
SYN = '16' # <syn>

# Log file path and name
LOGFILE = os.path.join(os.path.join(os.environ['USERPROFILE']),
                       'Desktop',
                       'SM10.log') 


# Luigs & Neumann SM10 device class
class LandNSM10:
    # Constructor
    def __init__(self, verbose=0, serial_debug=False):
        # Logging level (0: none | 1: console | 2: file | 3: console & file)
        self.verbose = verbose
        
        # Flag to specify whether serial commands should included in the log
        # for debugging purposes
        self.serial_debug = serial_debug
        
        # Should the log be written into a file?
        if verbose == 2 or verbose == 3:
            # Try opening or creating log file
            try:
                # Open or create log file
                self.log_file = open(LOGFILE, 'a')
                
                # File opened flag
                self.logging = True
            except:
                # Set log file to None
                self.log_file = None
                
                # File opened flag
                self.logging = False
                
                # Loging
                msg = 'Unable to open or create log file'
                self.write_log(msg)
        
        # Time to sleep after sending a serial command
        self.cmd_sleep = CMD_SLEEP
        
        # Try establishing a connection with the device
        try:
            # Open serial connection
            self.ser = sr.Serial(port=PORT,
                                 baudrate=BAUDRATE,
                                 bytesize=BYTESIZE,
                                 parity=PARITY,
                                 stopbits=STOPBITS,
                                 timeout=CONNECTION_TIMEOUT)
            
            # Connection established flag
            self.connected = True
            
            # Message
            msg = 'SM10 serial connection established'
        except:
            # Set serial connection to None
            self.ser = None
            
            # Connection established flag
            self.connected = False
            
            # Message
            msg = 'SM10 serial connection failed'
            
        # Logging
        self.write_log(msg)
            
        
    # Destructor
    def __del__(self):
        # Try closing serial connection
        try:
            # Close serial connection
            self.ser.close()
            
            # Logging
            msg = 'SM10 serial connection terminated'
            self.write_log(msg)
        except:
            pass
        
        # Try closing log file
        if self.logging:
            try:
                # Close log file
                self.log_file.close()
            except:
                pass
    
    
    # Write log (console and/or file)
    def write_log(self, msg):
        # Formated timestamp
        timestamp = '[' + time.strftime('%Y/%m/%d %H:%M:%S',
                                        time.localtime()) + '] '
        
        # Append input message <msg> to time stamp
        msg = timestamp + msg
        
        # Write on console
        if self.verbose == 1 or self.verbose == 3:
            print(msg)
        
        # Write in text file
        if ( self.verbose == 2 or self.verbose == 3 ) and self.logging:
            self.log_file.write(msg + '\n')
        
        return None


    # Send command to device
    def send_command(self, cmd_id, n_bytes, var_bytes, n_ret_bytes):
        # Check variable data byte-length for internal debugging purposes
        if n_bytes != len(var_bytes):
            # Logging
            if self.serial_debug:
                msg = '\t(Error in serial command: attempting to read '
                msg += '{0} byte(s) but {1} '.format(n_bytes, len(var_bytes))
                msg += 'is(were) sent)'
                self.write_log(msg)
                
            return None

        # Fixed part of the serial command:
        # <syn><ID><# of bytes>
        char_command = SYN + cmd_id + '%02x' % n_bytes
        
        # Variable part of the serial command:
        # (remember floating-point numbers are represented from LSB to MSB)
        for individual_bytes in var_bytes:
            char_command += '%02x' % individual_bytes
        
        # CRC (deprecated and here for backward compatibility according to
        #      Luigs and Neumann)
        LSB = 0
        MSB = 0
        CRC = (LSB, MSB)
        char_command += '%02x%02x' % CRC

        # Binarize serial command
        bin_command = binascii.unhexlify(char_command)
        
        # Write to serial port
        self.ser.write(bin_command)
        
        # Logging
        if self.serial_debug:
            msg = '\t(Sending: ' + char_command + ')'
            self.write_log(msg)
        
        # Time to sleep after sending a serial command
        time.sleep(self.cmd_sleep)
        
        # Read answer from device on serial port
        ans = self.ser.read(n_ret_bytes)

        # Return answer
        return ans


    # Position inquiry (0x0101)
    # Reads the position as displayed on the console of SM-10
    def position_inquiry(self, axis):
        # Command parameters
        cmd_id = '0101'
        n_bytes = 1
        n_ret_bytes = 10
        var_bytes = []
        
        # Axis number
        var_bytes.append(axis)
        
        # Logging
        msg = 'Query axis ' + str(axis) + ' position ...'
        self.write_log(msg)
        
        # Send command and read return bytes
        ans = self.send_command(cmd_id, n_bytes, var_bytes, n_ret_bytes)
        
        # Convert return bytes to floating-point position
        position = struct.unpack('f', ans[4:8])[0]

        # Logging
        msg = 'Axis ' + str(axis) + ' position = {0:.4f}'.format(position)
        self.write_log(msg)
        
        return position
    
    
    # Approaching a position (0x0048, 0x0049, 0x004a, and 0x004b)
    def approach_position(self,
                          axis,
                          position,
                          absolute=True,
                          slow=True,
                          reverse=False):
        # Message
        msg = '(axis: {0}) '.format(axis)
        
        # Command parameters
        if absolute and not slow:
            cmd_id = '0048'
            msg += 'Moving fast to absolute position: '
        elif absolute and slow:
            cmd_id = '0049'
            msg += 'Moving slow to absolute position: '
        elif not absolute and not slow:
            cmd_id = '004a'
            msg += 'Moving fast to relative position: '
        elif not absolute and slow:
            cmd_id = '004b'
            msg += 'Moving slow to relative position: '
            
        n_bytes = 5
        n_ret_bytes = 5
        var_bytes = []
        
        # Axis number
        var_bytes.append(axis)
        
        # Reverse axis if necessary
        if reverse:
            position = -position
            
        # Position represented by four decimal integers
        var_bytes.extend(self.float_to_dec_bytes(position))
        
        # Logging
        msg += '{0:+.4f} um'.format(position)
        self.write_log(msg)
        
        # Send command and read return bytes
        ans = self.send_command(cmd_id, n_bytes, var_bytes, n_ret_bytes)
        
        return ans
    
    
    # Inquiry about axis status (0x011e)
    def axis_status(self, axis):
        # Command parameters
        cmd_id = '011e'
        n_bytes = 1
        n_ret_bytes = 7
        var_bytes = []
        
        # Axis number
        var_bytes.append(axis)
        
        # Send command and read return bytes
        ans = self.send_command(cmd_id, n_bytes, var_bytes, n_ret_bytes)
        
        # Read axis status
        ans = ans[4]
        
        # Logging
        msg = 'Axis ' + str(axis) + ' status: '
        self.write_log(msg)
        
        return ans
    
    
    # Switching axis on/off (0x0034 and 0x0035)
    def axis_switch(self, axis, switch_on=True):
        # Command parameters
        if not switch_on:
            msg = 'Axis ' + str(axis) + ' switched OFF'
            cmd_id = '0034'
        elif switch_on:
            msg = 'Axis ' + str(axis) + ' switched ON'
            cmd_id = '0035'
        n_bytes = 1
        n_ret_bytes = 5
        var_bytes = []
        
        # Axis number
        var_bytes.append(axis)
        
        # Send command and read return bytes
        ans = self.send_command(cmd_id, n_bytes, var_bytes, n_ret_bytes)
        
        # Logging
        self.write_log(msg)
        
        return ans
    
    
    # Convert a float into bytes with a decimal representation
    def float_to_dec_bytes(self, number):
        # Convert a float into its hexadecimal representation
        hex_rep = binascii.hexlify(struct.pack('>f', number))
        
        # Convert the hexadecimal representation into decimal and reverse
        # the endianness (LSB to MSB)
        dec_rep = ([int(hex_rep[6:], 16),
                    int(hex_rep[4:6], 16),
                    int(hex_rep[2:4], 16),
                    int(hex_rep[:2], 16)])
        
        # I feel like there might be an easier way about this problem and
        # it feels redundant to go from Hex to Dec and then back to Hex
        # in the <send_command> function
        
        return dec_rep


# Main
def main():
    # Create and establish serial connection to new device
    my_device = LandNSM10(verbose=1, serial_debug=True)
    
    my_device.approach_position(15, -100, absolute=False)

    # Delete and terminate device connection
    del my_device
    
    return 0


if __name__ == "__main__":
    main()