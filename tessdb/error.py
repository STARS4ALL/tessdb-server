# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

class ValidationError(ValueError):
    pass
    
class ReadingKeyError(ValidationError):
    '''Missing mandatory keys in reading'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = '{0}: {1}'.format(s, str(self.args[0]))
        s = '{0}.'.format(s)
        return s

class ReadingTypeError(ValidationError):
    '''Reading, incorrect type value corresponding to key'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = '{0}: "{1}". Should be {2}, got {3}'.format(s, self.args[0], self.args[1], self.args[2])
        s = '{0}.'.format(s)
        return s
