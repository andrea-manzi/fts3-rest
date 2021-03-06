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

from fts3rest.tests import TestController
from fts3rest.lib.base import Session
from fts3.model import Job


class TestJobCancel(TestController):
    """
    Tests for the job cancellation
    """

    def _submit(self, count=1):
        """
        Submit a valid job
        """
        self.setup_gridsite_environment()
        self.push_delegation()

        files = []
        for i in xrange(count):
            files.append({
                'sources': ['root://source.es/file%d' % i],
                'destinations': ['root://dest.ch/file%d' % i],
                'selection_strategy': 'orderly',
                'checksum': 'adler32:1234',
                'filesize': 1024,
                'metadata': {'mykey': 'myvalue'},
            })

        job = {
            'files': files,
            'params': {'overwrite': True, 'verify_checksum': True}
        }

        answer = self.app.put(url="/jobs",
                              params=json.dumps(job),
                              status=200)

        # Make sure it was commited to the DB
        job_id = json.loads(answer.body)['job_id']
        return str(job_id)

    def test_cancel(self):
        """
        Cancel a job
        """
        job_id = self._submit()
        answer = self.app.delete(url="/jobs/%s" % job_id,
                                 status=200)
        job = json.loads(answer.body)

        self.assertEqual(job['job_id'], job_id)
        self.assertEqual(job['job_state'], 'CANCELED')
        self.assertEqual(job['reason'], 'Job canceled by the user')

        # Is it in the database?
        job = Session.query(Job).get(job_id)
        self.assertEqual(job.job_state, 'CANCELED')
        self.assertNotEqual(None, job.job_finished)
        self.assertNotEqual(None, job.finish_time)
        for f in job.files:
            self.assertEqual(f.file_state, 'CANCELED')
            self.assertNotEqual(None, f.job_finished)
            self.assertNotEqual(None, f.finish_time)

    def test_cancel_terminal(self):
        """
        Cancel a job with files in terminal state
        """
        job_id = self._submit()

        job = Session.query(Job).get(job_id)
        job.job_state = 'FINISHED'
        for f in job.files:
            f.file_state = 'FINISHED'
        Session.merge(job)
        Session.commit()

        answer = self.app.delete(url="/jobs/%s" % job_id,
                                 status=200)
        job = json.loads(answer.body)

        self.assertEqual(job['job_id'], job_id)
        self.assertEqual(job['job_state'], 'FINISHED')
        self.assertNotEqual(job['reason'], 'Job canceled by the user')

        # Is it in the database?
        job = Session.query(Job).get(job_id)
        self.assertEqual(job.job_state, 'FINISHED')
        for f in job.files:
            self.assertEqual(f.file_state, 'FINISHED')

    def test_cancel_some_terminal(self):
        """
        Cancel a job with some files in terminal state
        """
        job_id = self._submit(10)

        job = Session.query(Job).get(job_id)
        job.job_state = 'ACTIVE'
        for f in job.files:
            if f.file_id % 2 == 0:
                f.file_state = 'FINISHED'
        Session.merge(job)
        Session.commit()

        answer = self.app.delete(url="/jobs/%s" % job_id,
                                 status=200)
        job = json.loads(answer.body)

        self.assertEqual(job['job_id'], job_id)
        self.assertEqual(job['job_state'], 'CANCELED')
        self.assertEqual(job['reason'], 'Job canceled by the user')

        # Is it in the database?
        job = Session.query(Job).get(job_id)
        self.assertEqual(job.job_state, 'CANCELED')
        for f in job.files:
            if f.file_id % 2 == 0:
                self.assertEqual(f.file_state, 'FINISHED')
                self.assertNotEqual(f.reason, 'Job canceled by the user')
            else:
                self.assertEqual(f.file_state, 'CANCELED')

    def test_cancel_multiple(self):
        """
        Cancel multiple jobs at once
        """
        job_ids = list()
        for i in range(10):
          job_ids.append(self._submit())

        answer = self.app.delete(url="/jobs/%s" % ','.join(job_ids),
                                 status=200)
        jobs = json.loads(answer.body)

        self.assertEqual(len(jobs), 10)
        for job in jobs:
            self.assertEqual(job['job_state'], 'CANCELED')
            self.assertEqual(job['reason'], 'Job canceled by the user')

        for job_id in job_ids:
            job = Session.query(Job).get(job_id)
            self.assertEqual(job.job_state, 'CANCELED')
            self.assertEqual(job.reason, 'Job canceled by the user')
            for f in job.files:
                self.assertEqual(f.file_state, 'CANCELED')
                self.assertEqual(f.reason, 'Job canceled by the user')

    def test_cancel_multiple_one(self):
        """
        Use multiple cancellation convention but with only one
        """
        job_id = self._submit()

        answer = self.app.delete(url="/jobs/%s," % job_id,
                                 status=200)
        jobs = json.loads(answer.body)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['job_id'], job_id)
        self.assertEqual(jobs[0]['job_state'], 'CANCELED')
        self.assertEqual(jobs[0]['reason'], 'Job canceled by the user')

        job = Session.query(Job).get(job_id)
        self.assertEqual(job.job_state, 'CANCELED')
        self.assertEqual(job.reason, 'Job canceled by the user')

    def test_cancel_multiple_one_wrong(self):
        """
        Cancel multiple jobs, but one does not exist.
        One status per entry
        """
        job_id = self._submit()
        answer = self.app.delete(url="/jobs/%s,fake-fake-fake" % job_id,
                                 status=207)
        jobs = json.loads(answer.body)

        self.assertEqual(len(jobs), 2)

        for job in jobs:
            if job['job_id'] == job_id:
                self.assertEqual(job['job_state'], 'CANCELED')
                self.assertEqual(job['reason'], 'Job canceled by the user')
                self.assertEqual(job['http_status'], '200 Ok')
            else:
                self.assertEqual(job['http_status'], '404 Not Found')
