from datetime import datetime, timedelta
from fts3rest.tests import TestController
from fts3rest.lib.base import Session
from fts3.model import Credential, CredentialCache
from M2Crypto import EVP
from nose.plugins.skip import SkipTest
from routes import url_for
import json
import pytz
import time


class TestDelegation(TestController):
    
    def _get_termination_time(self, dlg_id):
        answer = self.app.get(url = url_for(controller = 'delegation', action = 'view', id = dlg_id))
        tt = datetime.strptime(str(json.loads(answer.body)['termination_time']), '%Y-%m-%dT%H:%M:%S')
        return tt.replace(tzinfo = pytz.UTC)


    def test_put_cred_without_cache(self):
        """
        This is a regression test. It tries to PUT directly
        credentials without the previous negotiation, so there is no
        CredentialCache in the database. This attempt must fail.
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()
        
        request = self.app.get(url = url_for(controller = 'delegation', action = 'request', id = creds.delegation_id),
                               status = 200)
        proxy = self.getX509Proxy(request.body)
        
        Session.delete(Session.query(CredentialCache).get((creds.delegation_id, creds.user_dn)))
        
        answer = self.app.put(url = url_for(controller = 'delegation', action = 'credential', id = creds.delegation_id),
                              params = proxy,
                              status = 400)


    def test_put_malformed_pem(self):
        """
        Putting a malformed proxy must fail
        """
        self.setupGridsiteEnvironment()       
        creds = self.getUserCredentials()
        
        request = self.app.get(url = url_for(controller = 'delegation', action = 'request', id = creds.delegation_id),
                               status = 200)
                
        answer = self.app.put(url = url_for(controller = 'delegation', action = 'credential', id = creds.delegation_id),
                              params = 'MALFORMED!!!1',
                              status = 400)
        
        
    def test_valid_proxy(self):
        """
        Putting a well-formed proxy with all the right steps must succeed
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()
        
        request = self.app.get(url = url_for(controller = 'delegation', action = 'request', id = creds.delegation_id),
                               status = 200)
        proxy = self.getX509Proxy(request.body)
        
        answer = self.app.put(url = url_for(controller = 'delegation', action = 'credential', id = creds.delegation_id),
                              params = proxy,
                              status = 201)
        
        proxy = Session.query(Credential).get((creds.delegation_id, creds.user_dn))
        self.assertNotEqual(None, proxy)
        return proxy

        
    def test_dn_mismatch(self):
        """
        A well-formed proxy with mismatching issuer and subject must fail
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()
        
        request = self.app.get(url = url_for(controller = 'delegation', action = 'request', id = creds.delegation_id),
                               status = 200)
        
        proxy = self.getX509Proxy(request.body, subject = [('DC', 'dummy')])
        
        answer = self.app.put(url = url_for(controller = 'delegation', action = 'credential', id = creds.delegation_id),
                              params = proxy,
                              status = 400)


    def test_signed_wrong_priv_key(self):
        """
        Regression for FTS-30
        If a proxy is signed with an invalid private key, reject it
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()
        
        request = self.app.get(url = url_for(controller = 'delegation', action = 'request', id = creds.delegation_id),
                               status = 200)
        
        proxy = self.getX509Proxy(request.body, private_key = EVP.PKey())
        
        answer = self.app.put(url = url_for(controller = 'delegation', action = 'credential', id = creds.delegation_id),
                              params = proxy,
                              status = 400)


    def test_get_request_different_dlg_id(self):
        """
        A user should be able only to get his/her own proxy request,
        and be denied any other.
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()

        request = self.app.get(url = url_for(controller = 'delegation', action = 'request', id = '12345xx'),
                               status = 403)


    def test_view_different_dlg_id(self):
        """
        A user should be able only to get his/her own delegation information.
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()

        request = self.app.get(url = url_for(controller = 'delegation', action = 'view', id = '12345xx'),
                               status = 403)


    def test_remove_delegation(self):
        """
        A user should be able to remove his/her proxy
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()
        
        self.test_valid_proxy()
        
        request = self.app.delete(url = url_for(controller = 'delegation', action = 'delete', id = creds.delegation_id),
                                  status = 204)
        
        request = self.app.delete(url = url_for(controller = 'delegation', action = 'delete', id = creds.delegation_id),
                                  status = 404)
        
        proxy = Session.query(Credential).get((creds.delegation_id, creds.user_dn))
        self.assertEqual(None, proxy)


    def test_set_voms(self):
        """
        The server must regenerate a proxy with VOMS extensions
        Need a real proxy for this one
        """
        self.setupGridsiteEnvironment()
        creds = self.getUserCredentials()
        
        # Need to push a real proxy :/
        proxy_pem = self.getRealX509Proxy()
        if proxy_pem is None:
            raise SkipTest('Could not get a valid real proxy for test_set_voms')
        
        proxy = Credential()
        proxy.dn = creds.user_dn
        proxy.dlg_id = creds.delegation_id
        proxy.termination_time = datetime.utcnow() + timedelta(hours = 1)
        proxy.proxy = proxy_pem;
        Session.merge(proxy)
        Session.commit()
        
        # Now, request the voms extensions
        request = self.app.post(url = url_for(controller = 'delegation', action = 'voms', id = creds.delegation_id),
                                content_type = 'application/json',
                                params = json.dumps(['dteam:/dteam/Role=lcgadmin']),
                                status = 203)

        # And validate
        proxy2 = Session.query(Credential).get((creds.delegation_id, creds.user_dn))
        self.assertNotEqual(proxy.proxy, proxy2.proxy)
        self.assertEqual('dteam:/dteam/Role=lcgadmin', proxy2.voms_attrs)
