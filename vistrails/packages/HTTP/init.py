############################################################################
##
## Copyright (C) 2006-2010 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at vistrails@sci.utah.edu.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################
"""HTTP provides packages for HTTP-based file fetching. This provides
a location-independent way of referring to files. This package uses a
local cache of the files, inside the per-user VisTrails
directory. This way, files that haven't been changed do not need
downloading. The check is performed efficiently using the HTTP GET
headers.
"""


from PyQt4 import QtGui
from core.modules.vistrails_module import ModuleError
from core.configuration import get_vistrails_persistent_configuration
from gui.utils import show_warning
import core.modules.vistrails_module
import core.modules
import core.modules.basic_modules
import core.modules.module_registry
import core.system
from core import debug
import gui.repository
import httplib
import urllib2
import os.path
import sys
import urllib
import socket
import datetime

import hashlib
# special file uploaders used to push files to repository
from core.repository.poster.encode import multipart_encode
from core.repository.poster.streaminghttp import register_openers

package_directory = None

class MyURLopener(urllib.FancyURLopener):
    """ Custom URLopener that enables urllib.urlretrieve to catch 404 errors"""
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        if errcode == 404:
            raise IOError, ('http error', errcode, errmsg, headers)
        # call parent method 
        urllib.FancyURLopener().http_error_default(url, fp, errcode,
                                                   errmsg, headers)

urllib._urlopener = MyURLopener()

###############################################################################

class HTTP(core.modules.vistrails_module.Module):
    pass

class HTTPFile(HTTP):
    """ Downloads file from URL """

    def __init__(self):
        HTTP.__init__(self)

    def parse_url(self, url):
        s = url.split('/')
        try:
            self.host = s[2]
            self.filename = '/' + '/'.join(s[3:])
        except:
            raise ModuleError(self, "Malformed URL: %s" % url)

    def is_outdated(self, remoteHeader, localFile):
        """Checks whether local file is outdated."""
        local_time = \
                datetime.datetime.utcfromtimestamp(os.path.getmtime(localFile))
        remote_time = datetime.datetime.strptime(remoteHeader,
                                                 "%a, %d %b %Y %H:%M:%S %Z")
        return remote_time > local_time

    def _file_is_in_local_cache(self, local_filename):
        return os.path.isfile(local_filename)

    def compute(self):
        self.checkInputPort('url')
        url = self.getInputFromPort("url")
        self.parse_url(url)
        conn = httplib.HTTPConnection(self.host)
        local_filename = package_directory + '/' + urllib.quote_plus(url)
        self.setResult("local_filename", local_filename)
        try:
            conn.request("GET", self.filename)
        except socket.gaierror, e:
            if self._file_is_in_local_cache(local_filename):
                debug.warning(('A network error occurred. HTTPFile will use'
                               ' cached version of file'))
                result = core.modules.basic_modules.File()
                result.name = local_filename
                self.setResult("file", result)
            else:
                raise ModuleError(self, e[1])
        else:
            response = conn.getresponse()
            mod_header = response.msg.getheader('last-modified')
            result = core.modules.basic_modules.File()
            result.name = local_filename
            if (not self._file_is_in_local_cache(local_filename) or
                not mod_header or
                self.is_outdated(mod_header, local_filename)):
                try:
                    urllib.urlretrieve(url, local_filename)
                except IOError, e:
                    raise ModuleError(self, ("Invalid URL: %s" % e))
                except:
                    raise ModuleError(self, ("Could not create local file '%s'" %
                                             local_filename))
            conn.close()
            self.setResult("file", result)

class RepoSync(HTTP):
    """ enables data to be synced with a online repository. The designated file
    parameter will be uploaded to the repository on execution,
    creating a new pipeline version that links to online repository data.
    If the local file isn't available, then the online repository data is used.
    """
    def __init__(self):
        HTTP.__init__(self)
        self.base_url = \
                get_vistrails_persistent_configuration().webRepositoryURL

        # TODO: this '/' check should probably be done in core/configuration.py
        if self.base_url[-1] == '/':
            self.base_url = self.base_url[:-1]

    # used for invaliding cache when user isn't logged in to crowdLabs
    # but wants to upload data
    def invalidate_cache(self):
        return False

    def validate_cache(self):
        return True

    def _file_is_in_local_cache(self, local_filename):
        return os.path.isfile(local_filename)

    def checksum_lookup(self):
        """ checks if the repository has the wanted data """

        checksum_url = "%s/datasets/exists/%s/" % (self.base_url, self.checksum)
        self.on_server = False
        try:
            check_dataset_on_repo = urllib2.urlopen(url=checksum_url)
            self.up_to_date = True if \
                    check_dataset_on_repo.read() == 'uptodate' else False
            self.on_server = True
            print 'checksum lookup'
        except urllib2.HTTPError:
            self.up_to_date = True
            print 'checksum lookup2'

    def data_sync(self):
        """ downloads/uploads/uses the local file depending on availability """
        self.checksum_lookup()

        # local file not on repository, so upload
        if not self.on_server and os.path.isfile(self.in_file.name):
            cookiejar = gui.repository.QRepositoryDialog.cookiejar
            if cookiejar:
                register_openers(cookiejar=cookiejar)

                params = {'dataset_file': open(self.in_file.name, 'rb'),
                          'name': self.in_file.name.split('/')[-1],
                          'origin': 'vistrails',
                          'checksum': self.checksum}

                upload_url = "%s/datasets/upload/" % self.base_url

                datagen, headers = multipart_encode(params)
                request = urllib2.Request(upload_url, datagen, headers)
                try:
                    result = urllib2.urlopen(request)
                    if result.code != 200:
                        show_warning("Upload Failure",
                                     "Data failed to upload to repository")
                        # make temporarily uncachable
                        self.is_cacheable = self.invalidate_cache
                    else:
                        debug.warning("Push to repository was successful")
                        # make sure module caches
                        self.is_cacheable = self.validate_cache
                except Exception, e:
                    show_warning("Upload Failure",
                                 "Data failed to upload to repository")
                    # make temporarily uncachable
                    self.is_cacheable = self.invalidate_cache
                debug.warning('RepoSync uploaded %s to the repository' % \
                              self.in_file.name)
            else:
                show_warning("Please login", ("You must be logged into the web"
                                              " repository in order to upload "
                                              "data. No data was synced"))
                # make temporarily uncachable
                self.is_cacheable = self.invalidate_cache

            # use local data
            self.setResult("file", self.in_file)
        else:
            # file on repository mirrors local file, so use local file
            if self.up_to_date and os.path.isfile(self.in_file.name):
                self.setResult("file", self.in_file)
            else:
                # local file not present or out of date, download or used cached
                self.url = "%s/datasets/download/%s" % (self.base_url,
                                                       self.checksum)
                local_filename = package_directory + '/' + \
                        urllib.quote_plus(self.url)
                if not self._file_is_in_local_cache(local_filename):
                    # file not in cache, download 
                    try:
                        urllib.urlretrieve(self.url, local_filename)
                    except IOError, e:
                        raise ModuleError(self, ("Invalid URL: %s" % e))
                out_file = core.modules.basic_modules.File()
                out_file.name = local_filename
                debug.warning('RepoSync is using repository data')
                self.setResult("file", out_file)

    def compute(self):
        self.checkInputPort('file')
        self.in_file = self.getInputFromPort("file")
        if os.path.isfile(self.in_file.name):
            # do size check
            size = os.path.getsize(self.in_file.name)
            if size > 10485760:
                show_warning("File is too large", ("file is larger than 10MB, "
                             "unable to sync with web repository"))
                self.setResult("file", self.in_file)
            else:
                # compute checksum
                f = open(self.in_file.name, 'r')
                self.checksum = hashlib.sha1()
                block = 1
                while block:
                    block = f.read(128)
                    self.checksum.update(block)
                f.close()
                self.checksum = self.checksum.hexdigest()

                # upload/download file
                self.data_sync()

                # set checksum param in module
                if not self.hasInputFromPort('checksum'):
                    self.change_parameter('checksum', [self.checksum])

        else:
            # local file not present
            if self.hasInputFromPort('checksum'):
                self.checksum = self.getInputFromPort("checksum")

                # download file
                self.data_sync()

def initialize(*args, **keywords):
    reg = core.modules.module_registry.get_module_registry()
    basic = core.modules.basic_modules

    reg.add_module(HTTP, abstract=True)
    reg.add_module(HTTPFile)
    reg.add_input_port(HTTPFile, "url", (basic.String, 'URL'))
    reg.add_output_port(HTTPFile, "file", (basic.File, 'local File object'))
    reg.add_output_port(HTTPFile, "local_filename",
                        (basic.String, 'local filename'), optional=True)

    reg.add_module(RepoSync)
    reg.add_input_port(RepoSync, "file", (basic.File, 'File'))
    reg.add_input_port(RepoSync, "checksum",
                       (basic.String, 'Checksum'), optional=True)
    reg.add_output_port(RepoSync, "file", (basic.File,
                                           'Repository Synced File object'))
    reg.add_output_port(RepoSync, "checksum",
                        (basic.String, 'Checksum'), optional=True)

    global package_directory
    package_directory = core.system.default_dot_vistrails() + "/HTTP"

    if not os.path.isdir(package_directory):
        try:
            print "Creating package directory..."
            os.mkdir(package_directory)
        except:
            print "Could not create package directory. Make sure"
            print "'%s' does not exist and parent directory is writable"
            sys.exit(1)
        print "Ok."


##############################################################################

import unittest


class TestHTTPFile(unittest.TestCase):

    class DummyView(object):
        def set_module_active(self, id):
            pass
        def set_module_computing(self, id):
            pass
        def set_module_success(self, id):
            pass
        def set_module_error(self, id, error):
            pass

    def testParseURL(self):
        foo = HTTPFile()
        foo.parse_url('http://www.sci.utah.edu/~cscheid/stuff/vtkdata-5.0.2.zip')
        self.assertEquals(foo.host, 'www.sci.utah.edu')
        self.assertEquals(foo.filename, '/~cscheid/stuff/vtkdata-5.0.2.zip')

    def testIncorrectURL(self):
        from core.db.locator import XMLFileLocator
        import core.vistrail
        from core.vistrail.module import Module
        from core.vistrail.module_function import ModuleFunction
        from core.vistrail.module_param import ModuleParam
        import core.interpreter
        p = core.vistrail.pipeline.Pipeline()
        m_param = ModuleParam(type='String',
                              val='http://illbetyouthisdoesnotexistohrly',
                              )
        m_function = ModuleFunction(name='url',
                                    parameters=[m_param],
                                    )
        p.add_module(Module(name='HTTPFile',
                           package=identifier,
                           id=0,
                           functions=[m_function],
                           ))
        interpreter = core.interpreter.default.get_default_interpreter()
        kwargs = {'locator': XMLFileLocator('foo'),
                  'current_version': 1L,
                  'view': self.DummyView(),
                  }
        interpreter.execute(p, **kwargs)

    def testIncorrectURL_2(self):
        import core.vistrail
        from core.db.locator import XMLFileLocator
        from core.vistrail.module import Module
        from core.vistrail.module_function import ModuleFunction
        from core.vistrail.module_param import ModuleParam
        import core.interpreter
        p = core.vistrail.pipeline.Pipeline()
        m_param = ModuleParam(type='String',
                              val='http://neitherodesthisohrly',
                              )
        m_function = ModuleFunction(name='url',
                                    parameters=[m_param],
                                    )
        p.add_module(Module(name='HTTPFile',
                           package=identifier,
                           id=0,
                           functions=[m_function],
                           ))
        interpreter = core.interpreter.default.get_default_interpreter()
        kwargs = {'locator': XMLFileLocator('foo'),
                  'current_version': 1L,
                  'view': self.DummyView(),
                  }
        interpreter.execute(p, **kwargs)

if __name__ == '__main__':
    unittest.main()