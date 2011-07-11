#!/usr/bin/python
###########################################################################
#
#    Copyright (C) 2009, 2010, 2011 Active Systems LLC, 
#    url: http://www.active.ee, email: info@active.ee
#
#    This file is part of OpenNode.
#
#    OpenNode is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OpenNode is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OpenNode.  If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################

"""Provide character based progress bar facility for OpenNode

Copyright 2011, Active Systems
Danel Ahman <danel@active.ee>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

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
