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

import sys

from fts3.rest.client import Inquirer
from base import Base
from utils import *


class JobShower(Base):

    def __init__(self):
        super(JobShower, self).__init__(extra_args='JOB_ID')

    def validate(self):
        if len(self.args) == 0:
            self.logger.critical('Need a job id')
            sys.exit(1)

    def run(self):
        job_id = self.args[0]
        context = self._create_context()

        inquirer = Inquirer(context)
        job      = inquirer.get_job_status(job_id, list_files=self.options.json)

        if not self.options.json:
            self.logger.info(job_human_readable(job))
        else:
            self.logger.info(job_as_json(job))
