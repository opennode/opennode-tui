"""Provide character based progress bar facility for OpenNode"""

def printProgressBar(percentage = 0, size = 30, remainingTime = -1):
    """Print progress bar in the form eg. [######       ] 50%"""
    split = size * percentage / 100
    i = 0
    #Start the bar with a [
    output = "["
    #Add #s according to done percentage 
    while (i < split):
        output = ''.join([output, '#'])
        i += 1
    #Add ' 's to the rest of the bar
    while (i < size):
       	output = ''.join([output, ' '])
       	i += 1
    #End the bar with a ] and print percentage in numbers
    output = ''.join([output, '] ', str(percentage), '% '])
    #Print the remaining time if it is given
    if (remainingTime > -1):
        hours = remainingTime / 3600
        remainingTime -= 3600 * hours
        minutes = remainingTime / 60
        remainingTime -= 60 * minutes
        seconds = remainingTime
        output = ''.join([output, 'ETA ', "%02d:%02d:%02d" % (hours, minutes, seconds)])
    return output
