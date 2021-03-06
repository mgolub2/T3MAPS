__author__ = 'Maximilian Golub','Bo Wang'
import serial

BAUD = 9600
<<<<<<< HEAD
COMPORT = '/dev/ptyp3'
VAL = 500
TIMEOUT = None;
#There are some predefined commands:
#To write data to the FPGA: 11111111
#The write command bit: 01111111
#This writes out to T3MAPS, and collects data
#To transmit data back to the computer: 01111110
=======
COMPORT = 5
TIMEOUT = None
MAXROWS = 64

pinDict = {0:'SRIN_ALL',
           1:'SRCK_G',
           2:'GCfgCK',
           3:'Dacld',
           4:'Stbld',
           5:'SlAltBus',
           6:'NU',
           7:'NU'}

"""There are some predefined commands:
To write data to the FPGA: 11111111
The write command bit: 01111111
This writes out to T3MAPS, and collects data
To transmit data back to the computer: 01111110"""

>>>>>>> State-Communication
RX = '11111111'
RX_OFF = '11111110'
WRITE = '01111111'
TRANSMIT = '01111110'


def generate_clock(length, n=1, start='0'):
    """Generates a clock pattern"""8
    if start not in ['0','1']:
        print "Invalid start specified for clock_pattern, using default '0'."
        start = '0'
    if start == '0':
        end = '1'
    else:
        end = '0'
    return ''.join((start*n + end*n for x in xrange(length)))

def binary_string(string,bits):
    """Creates a binary string"""
    b_string = bin(int(string))[2:]
    if(len(b_string) < bits):
        b_string = '0'*(bits-len(b_string))+b_string
    return b_string

def convertFPGAHits(data):
    """converts FPGA FF to 1 and otherwise 0"""
    final = ""
    for datum in data:
        temp = int(ord(datum))
        if(temp == 255):
            final+='1'
        elif(temp == 0):
            final+='0'
        else:
            raise Exception
    return final

class RawConversionException(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

def manual(port):
    """The manual method of controlling T3MAPS.
    The user must manually verify each step"""
    len_Data=commonSetup(port)
    Winput = raw_input("Write data to T3MAPS? (y/n): ")

    if (Winput.lower() == "y"):
        FPGA_write(port,WRITE,False)
        Winput2 = raw_input("Read data from FGPA fifo? (y/n): ")
        if (Winput2.lower() == "y"):
            readData(port,len_Data)
            port.close()
        else:
            print("Read aborted")
            port.close()
    else:
        print("Write aborted")
        port.close()

def auto(port):
    """The automatic method to write a stream to control T3MAPS.
    Will not lose data due to built in buffer in computer"""
    len_Data=commonSetup(port)
    readData(port, len_Data)

def commonSetup(port):
    """common setup between auto and manual"""
    port.close()
    port.open()
    commandString = configRead()
    byteCMDString = convertCMDString(commandString)
    return len_Data = FPGA_write(port,byteCMDString)

def readData(port,lenData):
    """Reads data from the serial port to a file."""
    shiftData = open('shiftData.txt', 'wb')
    FPGA_write(port,TRANSMIT,False)
    data = port.read(lenDatad)
    final = convertFPGAHits(data)
    shiftData.write(final)
    shiftData.close()

def convertToRaw(byte):
    """Converts 8 bits into a format that pyserial
       will convert into the correct pattern"""
    if(len(byte) == 8):
        temp = hex(int(byte, 2)) #Crazy but it works
        temp2 = temp[2:4]
        if (len(temp2) == 1):
            return ('0'+temp2).decode('hex')
        else:
            return temp2.decode('hex')
    else:
        raise RawConversionException

def convertCMDString(stringList):
    """Takes a string and converts it entirely to the raw bit format
    using the above method."""
    byteList = ''
    for x in range(0,len(stringList),8):
        byteList += convertToRaw(stringList[x:x+8])
    return byteList


def FPGA_write(port, commandString, RX_ON = True):
    """Writes data to the FPGA system using pyserial.
    By default, the method will assume that you
    need to use the RX flag. For testing purposes, using RX_ON
    False will result in just the byte you specify being sent."""
    if(port.isOpen()):
        if(RX_ON):
            port.write(convertToRaw(RX))
            bytesWritten = port.write(commandString)
            port.write(convertToRaw(RX_OFF))
            print(bytesWritten)
            return bytesWritten
        else:
            port.write(convertToRaw(commandString))
    else:
        print("Serial port failure")
        raise Exception

def configRead():
    """Generates the bit pattern from pix.py, then returns that pattern
    as a bitarray."""
    commandDict = _gen_command((get_dac_pattern()[::-1]+get_control_pattern(63)[::-1]), config = True)
    stringList = []
    for i in range(8):
        stringList.append(commandDict[pinDict[i]])
    shiftData = open('shiftData_before.txt', 'w')
    for s in pinDict.values():
        if (s != "NU"):
            shiftData.write(s+"\n")
            shiftData.write(commandDict[s]+"\n")
    shiftData.close()
    return convertToByte(stringList)


def get_control_pattern(col,hit_or = '0', hit='0',inject='0',tdac='00000',lden='0',S0='0',S1='0', hitld_in = '0', config_mode='00', global_readout_enable='0', count_hits_not='0', count_enable='0', count_clear_not='0', SRDO_load='0', NCout2='0', SRCLR_SEL='0', NCout21_25='00000'):
    """everything associated with count is not working, SRDO_load never used, SRCLR_SEL never used, NCout2 never used"""
    column_address = binary_string(col, 6)
    return global_readout_enable + SRDO_load + NCout2 + count_hits_not + count_enable + count_clear_not + S0 + S1 + config_mode + hit_or + hit + inject + tdac + lden + SRCLR_SEL + hitld_in + NCout21_25 + column_address


def get_dac_pattern(vth=150, DisVbn=49, VbpThStep=100, PrmpVbp=142, PrmpVbnFol=35, PrmpVbf=11): # fol35 vbp142 vbf11
    default=binary_string(129,8)# just for padding, no special meaning
    return default*4 + binary_string(DisVbn,8) + default*6 + binary_string(VbpThStep,8) + binary_string(PrmpVbp,8) + binary_string(PrmpVbnFol,8) + binary_string(vth,8) + binary_string(PrmpVbf,8) + default*2


def _gen_command(pattern, load_dacs=True, load_control=True, config=False):
    """Generate a command dictionary
    if config set true, generate a config command, else generate a column command
    a pulse on load_dacs loads the first 144 bit in the config shift register
    a pulse on load_control loads the last 32 bit in the config shift register"""
    load_dacs = '1' if load_dacs else '0'
    load_control = '1' if load_control else '0'
    SregPat=''.join([bit*2 for bit in pattern])+4*'0'
    ClkPat=generate_clock(len(pattern))+4*'0'

    # Make sure the load (ctrl and dac) are set correctly
    LDZeroLengthBefore= len(SregPat) - 3
    LDPat='0'*LDZeroLengthBefore + load_control*2+'0'
    LD_dacsPat='0'*LDZeroLengthBefore + load_dacs*2+'0'
    emptyPat='0'*len(LDPat)
    SlAltBusPat='1'*(len(LDPat)-1)+'0'

    if(config):
        commands_dict = {'Stbld':LDPat,'Dacld':LD_dacsPat,'GCfgCK':ClkPat,'SRIN_ALL':SregPat,'SRCK_G':emptyPat,'SlAltBus':SlAltBusPat,'NU':emptyPat}
    else:
        commands_dict = {'Stbld':emptyPat,'Dacld':emptyPat,'GCfgCK':emptyPat,'SRIN_ALL':SregPat,'SRCK_G':ClkPat,'SlAltBus':SlAltBusPat,'NU':emptyPat}
    return commands_dict

def convertToByte(list):
    s=""
    for i in range(len(list[0])):
        for j in range(len(list)-1,-1,-1):
            s+=(list[j][i])
    return s

#Call the main method upon execution.
if __name__ == "__main__":
    port = serial.Serial(port=COMPORT,baudrate=BAUD, bytesize=8,stopbits=1, timeout=TIMEOUT)
    manual(port)
