###############################################################################
##
## Copyright (C) 2011-2014, NYU-Poly.
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: contact@vistrails.org
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice, 
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright 
##    notice, this list of conditions and the following disclaimer in the 
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the University of Utah nor the names of its 
##    contributors may be used to endorse or promote products derived from 
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################

from datetime import date, datetime

from vistrails.core.system import strftime, time_strptime

class XMLDAO:
    def __init__(self):
        pass

    def hasAttribute(self, node, attr):
        return node.hasAttribute(attr)

    def getAttribute(self, node, attr):
        try:
            attribute = node.attributes.get(attr)
            if attribute is not None:
                return attribute.value
        except KeyError:
            pass
        return None

    def convertFromStr(self, value, type):
        if value is not None:
            if type == 'str':
                return str(value)
            elif value.strip() != '':
                if type == 'long':
                    return long(value)
                elif type == 'float':
                    return float(value)
                elif type == 'int':
                    try:
                        return int(value)
                    except ValueError:
                        if 'False' == value:
                            return -1
                        else:
                            return 0
                elif type == 'date':
                    return date(*time_strptime(value, '%Y-%m-%d')[0:3])
                elif type == 'datetime':
                   return datetime(*time_strptime(value, '%Y-%m-%d %H:%M:%S')[0:6])
        return None

    def convertToStr(self, value, type):
        if value is not None:
            if type == 'date':
                return value.isoformat()
            elif type == 'datetime':
                return strftime(value, '%Y-%m-%d %H:%M:%S')
            else:
                return str(value)
        return ''
