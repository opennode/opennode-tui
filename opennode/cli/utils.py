import os, errno
import commands
import ConfigParser

def mkdir_p(path):
    """Emulates mkdir -p. http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python"""
    try:
        os.makedirs(path)
    except OSError as exc: 
        if exc.errno == errno.EEXIST:
            pass
        else: raise

def execute(cmd):
    """ """
    status, output = commands.getstatusoutput(cmd)
    return status, output 

class SimpleConfigParser(ConfigParser.ConfigParser):
    """ Parses configuration file without sections. """
    COMMENT_CHAR = '#'
    OPTION_CHAR =  '='
    
    def __init__(self):
        super(SimpleConfigParser, self).__init__()
        self.options = {}
    
    def get(self, key):
        return self.options[key]
    
    def items(self):
        return self.options
    
    def read(self, filename):
        with open(filename) as configfile:
            for line in configfile:
                # First, remove comments:
                if self.COMMENT_CHAR in line:
                    # split on comment char, keep only the part before
                    line, comment = line.split(self.COMMENT_CHAR, 1)
                # Second, find lines with an option=value:
                if self.OPTION_CHAR in line:
                    # split on option char:
                    option, value = line.split(self.OPTION_CHAR, 1)
                    # strip spaces:
                    option = option.strip()
                    value = value.strip()
                    # store in dictionary:
                    self.options[option] = value
