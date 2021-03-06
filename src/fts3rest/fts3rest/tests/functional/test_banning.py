#   Copyright notice:
#   Copyright CERN, 2014.
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
import urllib
from datetime import datetime, timedelta

from fts3.model import BannedDN, BannedSE, Job, File
from fts3rest.lib.base import Session
from fts3rest.tests import TestController
from insert_job import insert_job


class TestBanning(TestController):
    """
    Tests for user and storage banning
    """

    def setUp(self):
        self.setup_gridsite_environment()

    def tearDown(self):
        TestController.tearDown(self)
        Session.query(BannedDN).delete()
        Session.query(BannedSE).delete()

    def test_ban_dn(self):
        """
        Just ban a DN and unban it, make sure changes go into the DB
        """
        answer = self.app.post(url='/ban/dn', params={'user_dn': '/DC=cern/CN=someone'}, status=200)
        canceled = json.loads(answer.body)
        self.assertEqual(0, len(canceled))

        banned = Session.query(BannedDN).get('/DC=cern/CN=someone')
        self.assertNotEqual(None, banned)
        self.assertEqual(self.get_user_credentials().user_dn, banned.admin_dn)

        self.app.delete(url="/ban/dn?user_dn=%s" % urllib.quote('/DC=cern/CN=someone'), status=204)
        banned = Session.query(BannedDN).get('/DC=cern/CN=someone')
        self.assertEqual(None, banned)

    def test_ban_dn_submission(self):
        """
        If a DN is banned, submissions from this user must not be accepted
        """
        banned = BannedDN()
        banned.dn = self.get_user_credentials().user_dn
        Session.merge(banned)
        Session.commit()

        self.push_delegation()
        self.app.post(url="/jobs", content_type='application/json', params='[]', status=403)

    def test_ban_self(self):
        """
        A user can not ban (him|her)self
        """
        user_dn = self.get_user_credentials().user_dn
        self.app.post(url='/ban/dn', params={'user_dn': user_dn}, status=409)

    def test_ban_dn_cancel(self):
        """
        Ban a DN that has transfers running, make sure they are canceled
        """
        jobs = list()
        jobs.append(
            insert_job('dteam', 'gsiftp://source', 'gsiftp://destination', 'SUBMITTED', user_dn='/DC=cern/CN=someone')
        )
        jobs.append(
            insert_job('dteam', 'gsiftp://source', 'gsiftp://destination2', 'ACTIVE', user_dn='/DC=cern/CN=someone')
        )
        jobs.append(
            insert_job('dteam', 'gsiftp://source', 'gsiftp://destination2', 'FAILED', duration=10, queued=20,
                       user_dn='/DC=cern/CN=someone')
        )

        answer = self.app.post(url="/ban/dn", params={'user_dn': '/DC=cern/CN=someone'}, status=200)
        canceled_ids = json.loads(answer.body)

        self.assertEqual(2, len(canceled_ids))
        self.assertIn(jobs[0], canceled_ids)
        self.assertIn(jobs[1], canceled_ids)
        self.assertNotIn(jobs[2], canceled_ids)

        for job_id in jobs[0:2]:
            job = Session.query(Job).get(job_id)
            files = Session.query(File).filter(File.job_id == job_id)
            self.assertEqual('CANCELED', job.job_state)
            self.assertNotEqual(None, job.job_finished)
            self.assertNotEqual(None, job.finish_time)
            self.assertEqual('User banned', job.reason)
            for f in files:
                self.assertEqual('CANCELED', f.file_state)
                self.assertNotEqual(None, f.job_finished)
                self.assertNotEqual(None, f.finish_time)
                self.assertEqual('User banned', f.reason)

        job = Session.query(Job).get(jobs[2])
        self.assertEqual(job.job_state, 'FAILED')
        files = Session.query(File).filter(File.job_id == job.job_id)
        for f in files:
            self.assertEqual('FAILED', f.file_state)

    def test_ban_se(self):
        """
        Just ban a SE and unban it, make sure changes go into the DB
        """
        answer = self.app.post(url="/ban/se", params={'storage': 'gsiftp://nowhere'}, status=200)
        canceled = json.loads(answer.body)
        self.assertEqual(0, len(canceled))

        banned = Session.query(BannedSE).get('gsiftp://nowhere')
        self.assertNotEqual(None, banned)
        self.assertEqual(self.get_user_credentials().user_dn, banned.admin_dn)
        self.assertEqual('CANCEL', banned.status)
        self.assertEqual(None, banned.vo)

        self.app.delete(url="/ban/se?storage=%s" % urllib.quote('gsiftp://nowhere'), status=204)
        banned = Session.query(BannedSE).get('gsiftp://nowhere')
        self.assertEqual(None, banned)

    def test_ban_se_vo(self):
        """
        Just ban a SE and unban it, specifying a VO
        """
        answer = self.app.post(url="/ban/se", params={'storage': 'gsiftp://nowhere', 'vo_name': 'dteam'}, status=200)
        canceled = json.loads(answer.body)
        self.assertEqual(0, len(canceled))

        banned = Session.query(BannedSE).get('gsiftp://nowhere')
        self.assertNotEqual(None, banned)
        self.assertEqual(self.get_user_credentials().user_dn, banned.admin_dn)
        self.assertEqual('CANCEL', banned.status)
        self.assertEqual('dteam', banned.vo)

        self.app.delete(url="/ban/se?storage=%s" % urllib.quote('gsiftp://nowhere'), status=204)
        banned = Session.query(BannedSE).get('gsiftp://nowhere')
        self.assertEqual(None, banned)

    def test_ban_se_cancel(self):
        """
        Ban a SE that has files queued, make sure they are canceled
        """
        jobs = list()
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination', 'SUBMITTED'))
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination2', 'ACTIVE'))
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination2', 'FAILED', duration=10, queued=20))

        answer = self.app.post(url="/ban/se", params={'storage': 'gsiftp://source'}, status=200)
        canceled_ids = json.loads(answer.body)

        self.assertEqual(2, len(canceled_ids))
        self.assertIn(jobs[0], canceled_ids)
        self.assertIn(jobs[1], canceled_ids)
        self.assertNotIn(jobs[2], canceled_ids)

        for job_id in jobs[0:2]:
            job = Session.query(Job).get(job_id)
            files = Session.query(File).filter(File.job_id == job_id)
            self.assertEqual('CANCELED', job.job_state)
            self.assertNotEqual(None, job.job_finished)
            self.assertNotEqual(None, job.finish_time)
            for f in files:
                self.assertEqual('CANCELED', f.file_state)
                self.assertNotEqual(None, f.job_finished)
                self.assertNotEqual(None, f.finish_time)
                self.assertEqual('Storage banned', f.reason)

        job = Session.query(Job).get(jobs[2])
        self.assertEqual(job.job_state, 'FAILED')
        files = Session.query(File).filter(File.job_id == job.job_id)
        for f in files:
            self.assertEqual('FAILED', f.file_state)

    def test_ban_se_partial_job(self):
        """
        Ban a SE that has files queued. If a job has other pairs, the job must remain!
        """
        job_id = insert_job(
            'dteam',
            multiple=[('gsiftp://source', 'gsiftp://destination'), ('gsiftp://other', 'gsiftp://destination')]
        )
        answer = self.app.post(url="/ban/se", params={'storage': 'gsiftp://source'}, status=200)
        canceled_ids = json.loads(answer.body)

        self.assertEqual(1, len(canceled_ids))
        self.assertEqual(job_id, canceled_ids[0])

        job = Session.query(Job).get(job_id)
        self.assertEqual('SUBMITTED', job.job_state)
        self.assertEqual(None, job.job_finished)
        self.assertEqual(None, job.finish_time)

        files = Session.query(File).filter(File.job_id == job_id)
        for f in files:
            if f.source_se == 'gsiftp://source':
                self.assertEqual('CANCELED', f.file_state)
                self.assertNotEqual(None, f.finish_time)
            else:
                self.assertEqual('SUBMITTED', f.file_state)
            self.assertEqual(None, f.job_finished)

    def test_ban_se_cancel_vo(self):
        """
        Cancel a SE that has files queued, make sure they are canceled (with VO)
        """
        jobs = list()
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination', 'SUBMITTED'))
        jobs.append(insert_job('atlas', 'gsiftp://source', 'gsiftp://destination', 'SUBMITTED'))
        jobs.append(insert_job('atlas', 'gsiftp://source', 'gsiftp://destination2', 'SUBMITTED'))

        answer = self.app.post(
            url="/ban/se",
            params={'storage': 'gsiftp://source', 'status': 'cancel', 'vo_name': 'dteam'},
            status=200
        )
        canceled_ids = json.loads(answer.body)

        self.assertEqual(1, len(canceled_ids))
        self.assertIn(jobs[0], canceled_ids)

        for job_id in jobs:
            job = Session.query(Job).get(job_id)
            files = Session.query(File).filter(File.job_id == job_id)

            if job_id in canceled_ids:
                self.assertEqual('CANCELED', job.job_state)
            else:
                self.assertEqual('SUBMITTED', job.job_state)
            for f in files:
                if job_id in canceled_ids:
                    self.assertEqual('CANCELED', f.file_state)
                else:
                    self.assertEqual('SUBMITTED', f.file_state)

    def test_ban_se_wait(self):
        """
        Ban a SE, but instead of canceling, give jobs some time to finish
        """
        jobs = list()
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination', 'SUBMITTED'))
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination2', 'ACTIVE'))
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination2', 'FAILED', duration=10, queued=20))

        answer = self.app.post(url="/ban/se", params={'storage': 'gsiftp://source', 'status': 'wait', 'timeout': 1234},
                               status=200)
        waiting_ids = json.loads(answer.body)

        self.assertEqual(2, len(waiting_ids))
        self.assertIn(jobs[0], waiting_ids)
        self.assertIn(jobs[1], waiting_ids)
        self.assertNotIn(jobs[2], waiting_ids)

        for job_id in jobs[0:2]:
            job = Session.query(Job).get(job_id)
            files = Session.query(File).filter(File.job_id == job_id)
            self.assertIn(job.job_state, ['ACTIVE', 'SUBMITTED'])
            self.assertEqual(None, job.job_finished)
            self.assertEqual(None, job.finish_time)
            for f in files:
                self.assertIn(f.file_state, ['ACTIVE', 'SUBMITTED'])
                self.assertEqual(None, f.job_finished)
                self.assertEqual(None, f.finish_time)
                self.assertEqual(1234, f.wait_timeout)
                self.assertGreater(f.wait_timestamp, datetime.utcnow() - timedelta(minutes=1))

        job = Session.query(Job).get(jobs[2])
        self.assertEqual(job.job_state, 'FAILED')
        files = Session.query(File).filter(File.job_id == job.job_id)
        for f in files:
            self.assertEqual('FAILED', f.file_state)

        banned = Session.query(BannedSE).get('gsiftp://source')
        self.assertEqual('WAIT', banned.status)
        self.assertEqual(1234, banned.wait_timeout)

    def test_ban_se_wait_vo(self):
        """
        Ban a SE, but instead of canceling, give jobs some time to finish (with VO)
        """
        jobs = list()
        jobs.append(insert_job('dteam', 'gsiftp://source', 'gsiftp://destination', 'SUBMITTED'))
        jobs.append(insert_job('atlas', 'gsiftp://source', 'gsiftp://destination', 'SUBMITTED'))
        jobs.append(insert_job('atlas', 'gsiftp://source', 'gsiftp://destination2', 'SUBMITTED'))

        answer = self.app.post(
            url="/ban/se",
            params={'storage': 'gsiftp://source', 'status': 'wait', 'vo_name': 'dteam', 'timeout': 33},
            status=200
        )
        waiting_ids = json.loads(answer.body)

        self.assertEqual(1, len(waiting_ids))
        self.assertIn(jobs[0], waiting_ids)

        for job_id in jobs:
            job = Session.query(Job).get(job_id)
            files = Session.query(File).filter(File.job_id == job_id)

            self.assertEqual('SUBMITTED', job.job_state)
            for f in files:
                self.assertEqual('SUBMITTED', f.file_state)
                if job_id in waiting_ids:
                    self.assertEqual(33, f.wait_timeout)
                else:
                    self.assertEqual(None, f.wait_timeout)

    def test_ban_se_no_submit(self):
        """
        Ban a SE. Submissions to/from se must not be accepted
        """
        self.push_delegation()

        self.app.post(url="/ban/se", params={'storage': 'gsiftp://source'}, status=200)

        job = {
            'files': [{
                'sources': ['gsiftp://source/path/'],
                'destinations': ['gsiftp://destination/file'],
            }]
        }
        self.app.post(url="/jobs", content_type='application/json', params=json.dumps(job), status=403)

        # The other way around
        job = {
            'files': [{
                'sources': ['gsiftp://destination/file'],
                'destinations': ['gsiftp://source/path/']
            }]
        }
        self.app.post(url="/jobs", content_type='application/json', params=json.dumps(job), status=403)

    def test_ban_se_with_submission(self):
        """
        Ban a SE but allowing submissions
        """
        self.push_delegation()

        self.app.post(
            url="/ban/se", params={'storage': 'gsiftp://source', 'status': 'wait', 'allow_submit': True},
            status=200
        )

        job = {
            'files': [{
                'sources': ['gsiftp://source/path/'],
                'destinations': ['gsiftp://destination/file'],
            }]
        }
        answer = self.app.post(url="/jobs", content_type='application/json', params=json.dumps(job), status=200)
        job_id = json.loads(answer.body)['job_id']

        files = Session.query(File).filter(File.job_id == job_id)
        for f in files:
            self.assertEqual(0, f.wait_timeout)
            self.assertGreater(f.wait_timestamp, datetime.utcnow() - timedelta(minutes=1))

        # The other way around
        job = {
            'files': [{
                'sources': ['gsiftp://destination/file'],
                'destinations': ['gsiftp://source/path/']
            }]
        }
        answer = self.app.post(url="/jobs", content_type='application/json', params=json.dumps(job), status=200)
        job_id = json.loads(answer.body)['job_id']

        files = Session.query(File).filter(File.job_id == job_id)
        for f in files:
            self.assertEqual(0, f.wait_timeout)
            self.assertGreater(f.wait_timestamp, datetime.utcnow() - timedelta(minutes=1))

    # Some requests that must be rejected
    def test_ban_dn_empty(self):
        """
        Banning with a missing dn must fail
        """
        self.app.post(url="/ban/dn", params={}, status=400)

    def test_unban_dn_empty(self):
        """
        Unbanning with a missing dn must fail
        """
        self.app.delete(url="/ban/dn", status=400)

    def test_ban_se_empty(self):
        """
        Ask for banning with a missing storage must fail
        """
        self.app.post(url="/ban/se", params={}, status=400)

    def test_unban_se_empty(self):
        """
        Unbanning with a missing se must fail
        """
        self.app.delete(url="/ban/se", status=400)

    def test_ban_se_bad_timeout(self):
        """
        Ban SE with invalid timeout values
        """
        self.app.post(
            url="/ban/se", params={'storage': 'gsiftp://source', 'status': 'wait', 'timeout': 'xxx'},
            status=400
        )
        self.app.post(
            url="/ban/se", params={'storage': 'gsiftp://source', 'status': 'wait', 'timeout': -1},
            status=400
        )

    def test_ban_se_cancel_and_submit(self):
        """
        Setting status = cancel and ask for allow_submit must fail
        """
        self.app.post(
            url="/ban/se", params={'storage': 'gsiftp://source', 'status': 'cancel', 'allow_submit': True},
            status=400
        )

    def test_ban_se_bad_status(self):
        """
        Unbanning with something else than cancel or wait must fail
        """
        self.app.post(
            url="/ban/se", params={'storage': 'gsiftp://source', 'status': 'blahblah'},
            status=400
        )
