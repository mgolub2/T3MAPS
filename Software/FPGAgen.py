__author__ = 'Maximilian Golub','Bo Wang'
import serial
import Command
import argparse
#######################################################################################################################
#Settings for serial communication, predefined FPGA commands and pin mapping
BAUD = 9600
COMPORT = 3
TIMEOUT = 5

"""There are some predefined commands:
To write data to the FPGA: 11111111
The write command bit: 01111111
This writes out to T3MAPS, and collects data
To transmit data back to the computer: 01111110"""
RX = '11111111'
RX_OFF = '11111110'
WRITE = '01111111'
TRANSMIT = '01111110'
TRANSMIT_OFF = '10111111'

#a dictionary of the command pin mapping
pinDict = {0:'SRIN_ALL',
           1:'SRCK_G',
           2:'GCfgCK',
           3:'Dacld',
           4:'Stbld',
           5:'NU',
           6:'NU',
           7:'NU'}
#######################################################################################################################
#RawConversionException class
class RawConversionException(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

#######################################################################################################################
#Conversion methods for serial communication
def convertToByte(list):
    """Takes a list and output the list as a data bus list"""
    cmd=""
    for i in range(len(list[0])):
        temp = ""
        for j in range(len(list)-1,-1,-1):
            temp+=(list[j][i])
        cmd+=(chr(int(temp,2)))
    return cmd

def convertFPGAHits(data):
    """converts readout output file FF to 1 and otherwise 0"""
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
########################################################################################################################
#Single Command generation methods
def commandRead(commandDict,sendFile):
    """Takes a dictionary of command constructed in Command.py and return a data bus list"""
    stringList = []
    for i in range(8):
        stringList.append(commandDict[pinDict[i]])
    for s in pinDict.values():
        if (s != "NU"):
            sendFile.write(s+"\n")
            sendFile.write(commandDict[s]+"\n")
    return convertToByte(stringList)

def convertToRaw(string):
    return chr(int(string,2))

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

def readData(port,lenData,readFile,if_read):
    """Reads data from the serial port to a file called shiftData.txt."""
    FPGA_write(port,TRANSMIT,False)
    data = port.read(lenData)
    if if_read:
        final = convertFPGAHits(data)
        readFile.write(final+"\n")

def commonSetup(port,commandDict,sendFile):
    """Common setup between auto and manual methods"""
    port.close()
    port.open()
    byteCMDString = commandRead(commandDict,sendFile)
    len_Data = FPGA_write(port,byteCMDString)
    return len_Data

def manual(port,commandDict,sendFile,readFile,if_read=True):
    """The manual method of controlling T3MAPS.
    The user must manually verify each step"""
    len_Data=commonSetup(port,commandDict,sendFile)
    Winput = raw_input("Write data to T3MAPS? (y/n): ")

    if (Winput.lower() == "y"):
        FPGA_write(port,WRITE,False)
        Winput2 = raw_input("Read data from FGPA fifo? (y/n): ")
        if (Winput2.lower() == "y"):
            readData(port,len_Data,readFile,if_read)
            port.close()
        else:
            print("Read aborted")
            port.close()
    else:
        print("Write aborted")
        port.close()

def auto(port,commandDict,sendFile,readFile,if_read=True):
    """The automatic method to write a stream to control T3MAPS.
Will not lose data due to built in buffer in computer"""
    len_Data=commonSetup(port,commandDict,sendFile)
    readData(port, len_Data,readFile,if_read)


def analog_Test(port,type):
    if type == 'small':
        auto(port,Command.set_config(vth=150, config_mode = '11')) #for small pixel
    elif type == 'large':
        auto(port,Command.set_config(150, PrmpVbp = 244, PrmpVbf = 1, config_mode = '11'))#for large pixel
    auto(port,Command.hitor_hit_inject(is_hit_or=True,all=True,enable=True))
    auto(port,Command.hitor_hit_inject(is_hit_or=False,all=True,enable=False))

def Test_Pattern_Gcfg(args):
    """This is to run the system with test patterns for Gcfg Register, it will
    output a 1 at an index starting from 0, this way we can verify if that specific
    bit is at the right place when we read it back"""
    sendFile=open(args.sendFile,"wb")
    readFile=open(args.readFile,"wb")
    if(args.num>176):
        raise Exception
    for i in range(0,args.num):
        sendFile.write(str(i)+": \n")
        auto(args.port,Command.Gcfg_Test(i),sendFile,readFile,if_read=False)
        readFile.write(str(i)+": \n")
        auto(args.port,Command.Gcfg_Test(i),sendFile,readFile)
        readFile.write("\n")
        sendFile.write("\n")
    sendFile.close()
    readFile.close()


def Test_Pattern_Column(args):
    sendFile=open(args.sendFile,"wb")
    readFile=open(args.readFile,"wb")
    if(args.num>64):
        raise Exception
    for i in range(0,args.num):
        sendFile.write(str(i)+": \n")
        auto(args.port,Command.command_Dict_combine(Command.point_to_column(args.col,"00"),Command.Column_Array_Test(i,1),Command.extraclk(64)),sendFile,readFile,if_read=False)
        #auto(args.port,Command.point_to_column(args.col,"00"),sendFile,readFile,if_read=False)
	#auto(args.port,Command.Column_Array_Test(i,1),sendFile,readFile,if_read=False)
        readFile.write(str(i)+": \n")
        auto(args.port,Command.Column_Array_Test(i,1),sendFile,readFile)
        readFile.write("\n")
        sendFile.write("\n")
    sendFile.close()
    readFile.close()

def main_setup(args):
    print " Orient the chip, so that VDDA VDDD is in the correct position"
    print "  The power supply on the right should be connected to 1.5V (J30,J29)"
    print "  Another choice is to connect the left pin of J57 and J56 to 1.5V and the right pin to GND"
    print "  Make Sure SelAltBus is connected to the inner pin(Inner pin is connected to VDDD)"
    print "  The substrate supply on the left should not be floating, connect it to ground (J33)\n"
    print "  Check PinDict in code, modify it to suit your own need\n"
    print "  Connect the specified command number pin on adapter card to the specified pin on T3MAPS"

def set_config(args):
    sendFile=open(args.sendFile,"wb")
    readFile=open(args.readFile,"wb")
    auto(args.port,Command.set_config(),sendFile,readFile)

#Call the main method upon execution.
if __name__ == "__main__":
    port = serial.Serial(port=COMPORT,baudrate=BAUD, bytesize=8,stopbits=2, timeout=TIMEOUT)

    parser = argparse.ArgumentParser(description="Present a few options from FPGAgen.py to be used from the command line for testing..")
    parser.set_defaults(port=port)
    subparsers = parser.add_subparsers(title = 'Functions')

    setup = subparsers.add_parser('setup', help='Print instructions for the physical setup of the chip.')
    setup.set_defaults(func=main_setup)

    config_test = subparsers.add_parser('config_test', help='Test the outer configuration register, Input at SRIN_ALL, output at GcfgDout')
    config_test.set_defaults(func=Test_Pattern_Gcfg)
    config_test.add_argument('--num', dest='num', type=int, default=1, help='Number of test you want to perform, each '
     'test is only one 1 at the specific index, and 0s elsewhere. So if you set num=2, then you will be testing two times, first time with 1 at index 0, second time with 1 at index 1')
    config_test.add_argument('--sendFile',dest='sendFile',type=str, default='shiftData_before.txt', help='file to store sent data')
    config_test.add_argument('--readFile',dest='readFile',type=str, default='shiftData.txt',help='file to store data read back')

    column_test = subparsers.add_parser("column_test", help='Test the inner column shift register, Input at SRIN_ALL, output at SR_OUT')
    column_test.set_defaults(func=Test_Pattern_Column)
    column_test.add_argument('--col',dest='col',type=int,default=0,help='Column you wish to test')
    column_test.add_argument('--num', dest='num', type=int, default=1, help='Number of test you want to perform, each '
     'test is only one 1 at the specific index, and 0s elsewhere. So if you set num=2, then you will be testing two times, first time with 1 at index 0, second time with 1 at index 1')
    column_test.add_argument('--sendFile',dest='sendFile',type=str, default='shiftData_before.txt', help='file to store sent data')
    column_test.add_argument('--readFile',dest='readFile',type=str, default='shiftData.txt',help='file to store data read back')

    config = subparsers.add_parser("set_config", help='Set configuration for T3MAPS, 20mA current expected')
    config.set_defaults(func=set_config)
    config.add_argument('--sendFile',dest='sendFile',type=str, default='shiftData_before.txt', help='file to store sent data')
    config.add_argument('--readFile',dest='readFile',type=str, default='shiftData.txt',help='file to store data read back')

    args = parser.parse_args()
    args.func(args)