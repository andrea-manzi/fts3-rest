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

from fts3rest.lib.api import SubmitSchema
import unittest
import jsonschema


class TestJsonSchema(unittest.TestCase):
    """
    Use jsonschema to check that the JSON-Schema provided by the API
    is correct.
    """

    def setUp(self):
        self.data = {"files": [
                        {
                          "sources": ["srm://srm.grid.sara.nl:8443/pnfs/grid.sara.nl/data/dteam/test.rand"],
                          "destinations": ["gsiftp://lxbra1910.cern.ch/lxbra1910.cern.ch:/tmp/file.aalvarez.copy"],
                          "metadata": {"issuer": "aalvarez"},
                          "filesize": 1048576,
                          "checksum": "adler32:36603040"
                        }
                      ],
                      "params": {
                        "verify_checksum": True,
                        "reuse": False,
                        "spacetoken": None,
                        "bring_online": None,
                        "copy_pin_lifetime": -1,
                        "job_metadata": {"activity": "test"},
                        "source_spacetoken": None,
                        "overwrite": True,
                        "gridftp": None,
                        "multihop": True
                      }
                    }
        self.schema = SubmitSchema


    def test_validation(self):
        """
        Regular job must validate
        """
        jsonschema.validate(self.data, self.schema)


    #def test_missing_files(self):
    #    del self.data['files']
    #    self.assertRaises(jsonschema.ValidationError, jsonschema.validate, self.data, self.schema)


    def test_missing_params(self):
        """
        A job without extra parameters is valid
        """
        del self.data['params']
        jsonschema.validate(self.data, self.schema)


    def test_bad_reuse(self):
        """
        reuse parameter expects a boolean
        """
        self.data['params']['reuse'] = 'A string'
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate, self.data, self.schema)


    def test_files_not_array(self):
        """
        files expect an array
        """
        self.data['files'] = self.data['files'][0]
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate, self.data, self.schema)


    def test_source_not_array(self):
        """
        sources expecteds an array of urls
        """
        self.data['files'][0]['sources'] = 'srm://srm.grid.sara.nl:8443/pnfs/grid.sara.nl/data/dteam/test.rand'
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate, self.data, self.schema)
