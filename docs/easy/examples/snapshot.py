#!/usr/bin/env python
#
# How to query whoami
#

#   Copyright notice:
#   Copyright CERN, 2014.
#
#   See www.eu-emi.eu for details on the copyright holders
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import json
import logging
import fts3.rest.client.easy as fts3
from optparse import OptionParser


opts = OptionParser()
opts.add_option('-s', '--endpoint', dest='endpoint', default='https://fts3-pilot.cern.ch:8446')

(options, args) = opts.parse_args()

logging.getLogger('fts3.rest.client').setLevel(logging.DEBUG)

context = fts3.Context(options.endpoint)
snapshot = fts3.get_snapshot(context)
print json.dumps(snapshot, indent=2)
