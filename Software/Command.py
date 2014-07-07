__author__ = 'Maximilian Golub','Bo Wang'

from collections import defaultdict

#Number of rows in each pixel column
MAXROWS = 64

#These are bits that are not used in command generation, Everything associated with count is not working
GLOBAL_READOUT_ENABLE='0'
SRDO_LOAD='0'
NCOUT2='0'
COUNT_HITS_NOT='0'
COUNT_ENABLE='0'
COUNT_CLEAR_NOT='0'
SRCLR_SEL='0'
NCOUT21_25='00000'
LSB_SIX_BITS=GLOBAL_READOUT_ENABLE+SRDO_LOAD+NCOUT2+COUNT_HITS_NOT+COUNT_ENABLE+COUNT_CLEAR_NOT
CLOCK_UNIT_DURATION = 4
LEN_CONFIG = 720
LEN_COLUMN = 260

#######################################################################################################################
# Utility Functions
def generate_clock(length, n=1, start='0'):
    """Generate a clock pattern with n*2 bits as a period"""
    if start not in ['0','1']:
        print "Invalid start specified for clock_pattern, using default '0'."
        start = '0'
    if start == '0':
        end = '1'
    else:
        end = '0'
    return ''.join((start*n + end*n for x in xrange(length)))

def binary_string(string,bits):
    """Convert a string or integer to it's binary string form
    of n bits"""
    b_string = bin(int(string))[2:]
    if(len(b_string) < bits):
        b_string = '0'*(bits-len(b_string))+b_string
    return b_string
def repeat_each(string,n):
    """repeat each bit n times"""
    return "".join([s*n for s in string])
#######################################################################################################################
# Basic Command construction
# Commands are reversed because we are using a shift register
def get_control_pattern(col,hit_or = '0', hit='0',inject='0',lden='0',S0='0',S1='0', hitld_in = '0', config_mode='00',TDAC="00000"):
    """This is the last 32 bits(Counting from LSB) out of 176 bits in the configuration register
    Whenever you want to generate a pixel command, you have to set the configuration first
    Every parameter can be found in FEI4 manual, lden is the load enable signal for pixel register"""
    column_address = binary_string(col, 6)
    return (LSB_SIX_BITS + S0 + S1 + config_mode + hit_or + hit + inject + TDAC + lden + SRCLR_SEL + hitld_in + NCOUT21_25 + column_address)[::-1]

def get_dac_pattern(vth=150, DisVbn=49, VbpThStep=100, PrmpVbp=142, PrmpVbnFol=35, PrmpVbf=11, empty = False): # fol35 vbp142 vbf11
    """This is the first 144bit(Counting from LSB) out of 176 bits in the configuration register,
    It is only called once during the set_config command, and never changed afterwards
    If empty is true, generate 144 bit 0s,
    8 zeros at the front is to pull down the voltage"""
    default=binary_string(129,8)# just for padding, no special meaning
    if empty:
        return "0"*144
    else:
        return ("00000000"+default*3 + binary_string(DisVbn,8) + default*6 + binary_string(VbpThStep,8) + binary_string(PrmpVbp,8) + binary_string(PrmpVbnFol,8) + binary_string(vth,8) + binary_string(PrmpVbf,8) + default+"00000000")[::-1]

#######################################################################################################################
#CommandDict Generation and combine
def gen_config_command(pattern, load_dacs=False, load_control=True):
    """Generate a config command dictionary
    a pulse on load_dacs loads the first 144 bits in the config shift register
    a pulse on load_control loads the last 32 bits in the config shift register
    By default, this does not load the first 144 bits"""
    load_dacs = '1' if load_dacs else '0'
    load_control = '1' if load_control else '0'

    SregData=repeat_each(pattern,CLOCK_UNIT_DURATION)
    SregPat=SregData+'0'*(LEN_CONFIG-len(SregData)-1)
    SregPat='0'+SregPat

    ClkData=generate_clock(len(pattern),CLOCK_UNIT_DURATION/2)
    ClkPat=ClkData+'0'*(LEN_CONFIG-len(ClkData))

    # Make sure the load (ctrl and dac) are set correctly 
    LDZeroLengthBefore=len(ClkData) + 2
    LDPatLength=4
    LDPat='0'*LDZeroLengthBefore + load_control*LDPatLength + '0'*(LEN_CONFIG-LDZeroLengthBefore-LDPatLength)
    LD_dacsPat='0'*LDZeroLengthBefore + load_dacs*LDPatLength + '0'*(LEN_CONFIG-LDZeroLengthBefore-LDPatLength)
    emptyPat='0'*len(LDPat)

    commands = {'Stbld':LDPat,'Dacld':LD_dacsPat,'GCfgCK':ClkPat,'SRIN_ALL':SregPat,'SRCK_G':emptyPat,'NU':emptyPat}

    return commands

def gen_column_command(pattern):
    """Generate a command which will be used to program a column."""
    if len(pattern) != MAXROWS:
        print "Invalid pattern length for program_column (should be %i). Appending zeroes." % MAXROWS
        pattern += '0'*(MAXROWS - len(pattern))

    colSreg=pattern[::-1]
    SregData=repeat_each(colSreg,CLOCK_UNIT_DURATION)
    SregPat=SregData+'0'*(LEN_COLUMN-len(SregData)-1)
    SregPat='0'+SregPat
    ClkData=generate_clock(len(colSreg),CLOCK_UNIT_DURATION/2)
    ClkPat= ClkData+'0'*(LEN_COLUMN-len(ClkData))
    emptyPat='0'*len(ClkPat)

    commands = {'Stbld':emptyPat,'Dacld':emptyPat,'GCfgCK':emptyPat,'SRIN_ALL':SregPat,'SRCK_G':ClkPat,'NU':emptyPat}

    return commands
    
def command_Dict_combine(*args):
    """Combining multiple command dictionaries, this used in more complex commands associated with pixel commands"""
    combined_dict=defaultdict(str)
    for dict in args:
        for key in dict.keys():
            combined_dict[key]+=dict[key]
    return combined_dict
########################################################################################################################
#Complex command dictionary generation
def set_config(vth=150,PrmpVbp=142,PrmpVbf=11,config_mode="00"):
    return gen_config_command(get_dac_pattern(vth=vth,PrmpVbp=PrmpVbp,PrmpVbf=PrmpVbf)+get_control_pattern(63,config_mode=config_mode),load_dacs=True)

def point_to_column(col,config_mode):
    """Used only in pixel commands to point the shift_register to correct column"""
    return gen_config_command(get_dac_pattern(empty=True)+get_control_pattern(col,config_mode=config_mode))

def load_ldbus(col,hit_or,hit,inject):
    return gen_config_command(get_dac_pattern(empty=True)+get_control_pattern(col,hit_or=str(hit_or),hit=str(hit),inject=str(inject),lden="1"))

def Gcfg_Test(index):
    """A bitpattern of a '1' only at the associated index, this is only used to test the shift register, check if everything is working
    Clock into GcfgCK, Data into SRIN_ALL, Readout GcfgCK, DO NOT LOAD PATTERN
    Index Starts at 0
    """
    return gen_config_command('0'*index+'1'+'0'*(175-index),load_control=False)

def Column_Array_Test(row,num):
    """A bitpattern of a '1' only at the associated index, this is only used to test the column register, check if everything is working"""

    col_pat='0'*row+'1'*num+'1'*(MAXROWS-row-num)
    return gen_column_command(col_pat)
