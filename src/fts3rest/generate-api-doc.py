#!/usr/bin/env python

#   Copyright notice:
#   Copyright  Members of the EMI Collaboration, 2013.
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
import os
from fts3rest.lib import api
from optparse import OptionParser


def write_resources(options, resources):
    resource_index = os.path.join(options.output_directory, options.index)
    
    swagger_resources = {
        'swaggerVersion': '1.2',
        'apis': resources,
        'info': {
            'title': 'FTS3 RESTful API',
            'description': 'FTS3 RESTful API documentation',
            'contact': 'fts-devel@cern.ch',
            'license': 'Apache 2.0',
            'licenseUrl': 'http://www.apache.org/licenses/LICENSE-2.0.html'
        }
    }
    
    open(resource_index, 'wt').write(json.dumps(swagger_resources, indent=2, sort_keys=True))


def write_apis(options, resources, apis, models):
    for resource in resources:
        resource_path = resource['path']
        swagger_api = {
           'swaggerVersion': '1.2',
           'produces': ['application/json'],
           'resourcePath': resource_path,
           'authorizations': {},
           'apis': apis.get(resource_path, []),
           'models': models.get(resource_path, []),
        }
        
        api_path = os.path.join(options.output_directory, resource_path.strip('/'))
        open(api_path, 'wt').write(json.dumps(swagger_api, indent=2, sort_keys = True))


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-d', '--directory', dest='output_directory', default=None,
                      help='Where to write the output files. This is mandatory.')
    parser.add_option('-f', '--file', dest='index', default='resources.json',
                      help='Name of the resources file')
    
    (options, args) = parser.parse_args()
    if options.output_directory is None:
        parser.print_help()
        parser.exit(1)

    resources, apis, models = api.introspect()

    resources.sort(key=lambda r:r['path'])
    for api in apis.values():
        api.sort(key=lambda a:a['path'])
    
    write_resources(options, resources)
    write_apis(options, resources, apis, models)
