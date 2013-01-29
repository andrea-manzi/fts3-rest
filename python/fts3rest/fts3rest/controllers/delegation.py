from fts3.orm import CredentialCache, Credential
from fts3rest.lib.base import BaseController, Session
from M2Crypto import X509, RSA, EVP
from pylons.decorators import rest
from pylons import request
import uuid


def getDNComponents(dn):
	return map(lambda x: tuple(x.split('=')), dn.split('/')[1:])



def populatedName(components):
	x509Name = X509.X509_Name()
	for (field, value) in components:
		x509Name.add_entry_by_txt(field, 0x1000, value, len = -1, loc = -1, set = 0)
	return x509Name



def generateProxyRequest(userDN):
	components = getDNComponents(userDN)
	components.append(('CN', 'proxy'))
	
	requestKeyPair = RSA.gen_key(1024, 65537)
	requestPKey = EVP.PKey()
	requestPKey.assign_rsa(requestKeyPair)
	request = X509.Request()
	request.set_pubkey(requestPKey)	
	request.set_subject(populatedName(components))
	request.set_version(2)
	request.sign(requestPKey, 'sha1')
	
	return (request, requestPKey)


X509_SUBJECT = '/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=aalvarez/CN=678984/CN=Alejandro Alvarez Ayllon/CN=proxy'


class DelegationController(BaseController):
	
	def request(self, start_response):
		# Hardcoded for development
		(proxyRequest, proxyKey) = generateProxyRequest(X509_SUBJECT)
		
		# Register in the database
		credentialCache = CredentialCache(dlg_id = uuid.uuid1(),
										  dn = X509_SUBJECT,
										  cert_request = proxyRequest.as_pem(),
										  priv_key     = proxyKey.as_pem(cipher = None),
										  voms_attrs   = '') 
		
		start_response('200 OK', [('X-Delegation-ID', credentialCache.dlg_id)])

		#Session.add(credentialCache)
		#Session.commit()
		
		return proxyRequest.as_pem()
	
	
	@rest.restrict('PUT')
	def credential(self, start_response, delegation_id = None):
		if id is None:
			raise Exception
		
		x509ProxyPEM = request.body
		x509Proxy    = X509.load_cert_string(x509ProxyPEM)
		
		# Save
		credential = Credential(dlg_id           = delegation_id,
								dn               = X509_SUBJECT,
								proxy            = x509ProxyPEM,
								voms_attrs       = '',
								termination_time = x509Proxy.get_not_after().get_datetime())
		
		Session.add(credential)
		Session.commit()
		
		start_response('201 CREATED', [])
		
		return ''
	