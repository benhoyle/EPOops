import ConfigParser
import urllib, urllib2
import httplib
import json
import base64
from xml.dom.minidom import Document, parseString
import logging
import time

class EPOops():
	
	def __init__(self, filename):
		#filename is the filename of the list of publication numbers
		
		#Load Settings
		parser = ConfigParser.SafeConfigParser()
		parser.read('config.ini')
		self.consumer_key = parser.get('Login Parameters', 'C_KEY')
		self.consumer_secret = parser.get('Login Parameters', 'C_SECRET')
		self.host = parser.get('URLs', 'HOST')
		self.auth_url = parser.get('URLs', 'AUTH_URL')
		
		#Set filename
		self.filename = filename
		
		#Initialise list for classification strings
		self.c_list = []
		
		#Initialise new dom document for classification XML
		self.save_doc = Document()

		root = self.save_doc.createElement('classifications')
		self.save_doc.appendChild(root)

	def authorise(self):
		b64string = base64.b64encode(":".join([self.consumer_key, self.consumer_secret]))
		logging.error(self.consumer_key + self.consumer_secret + "\n" + b64string)
		#urllib2 method was not working - returning an error that grant_type was missing
		#request = urllib2.Request(AUTH_URL)
		#request.add_header("Authorization", "Basic %s" % b64string)
		#request.add_header("Content-Type", "application/x-www-form-urlencoded")
		#result = urllib2.urlopen(request, data="grant_type=client_credentials")
		logging.error(self.host + ":" + self.auth_url)
		
		#Use urllib method instead - this works
		params = urllib.urlencode({'grant_type' : 'client_credentials'})
		req = httplib.HTTPSConnection(self.host)
		req.putrequest("POST", self.auth_url)
		req.putheader("Host", self.host)
		req.putheader("User-Agent", "Python urllib")
		req.putheader("Authorization", "Basic %s" % b64string)
		req.putheader("Content-Type" ,"application/x-www-form-urlencoded;charset=UTF-8")
		req.putheader("Content-Length", "29")
		req.putheader("Accept-Encoding", "utf-8")
	
		req.endheaders()
		req.send(params)
		
		resp = req.getresponse()
		params = resp.read()
		logging.error(params)
		params_dict = json.loads(params)
		self.access_token = params_dict['access_token']
		
	def get_data(self, number):
		data_url = "/3.1/rest-services/published-data/publication/epodoc/"
		request_type = "/biblio"
		request = urllib2.Request("https://ops.epo.org" + data_url + number + request_type)
		request.add_header("Authorization", "Bearer %s" % self.access_token)
		logging.error(request.get_full_url())
		try:
			resp = urllib2.urlopen(request)
		except urllib2.HTTPError, error:
			error_msg = error.read()
			if "invalid_access_token" in error_msg:
				self.authorise()
				resp = urllib2.urlopen(request)
				
		#parse returned XML in resp
		XML_data = resp.read()
		return XML_data
		
	def extract_classification(self, xml_str):
		#extract the <patent-classification> elements
		dom = parseString(xml_str)
		#Select first publication for classification extraction
		first_pub = dom.getElementsByTagName('exchange-document')[0]
		self.c_list = self.c_list + [node.childNodes[1].childNodes[0].nodeValue for node in first_pub.getElementsByTagName('classification-ipcr')]
		#for node in first_pub.getElementsByTagName('classification-ipcr'):
			#node.childNodes[1].childNodes[0].nodeValue
			#G11B  27/    00            A I                    
			#G11B  23/    28            A I                    
			#G11B  27/    11            A I
		
		for node in first_pub.getElementsByTagName('patent-classification'):
			self.save_doc.firstChild.appendChild(node)
			
	def total_classifications(self):
		number_list = []
		
		#Get list of publication numbers - file name when initialising object?
		with open("cases.txt", "r") as f:
			for line in f:
				number_list.append(line.replace("/",""))
		
		for number in number_list:
			logging.error(number)
			XML_data = self.get_data(number.strip())
			#time.sleep(1) 
			self.extract_classification(XML_data)
		
		#Save list to file
		with open("classification_list.txt", "wb") as f:
			f.write("\n".join(str(x) for x in self.c_list))
		
		#Save xmldoc to file
		with open("save_doc.xml", "wb") as f:
			self.save_doc.writexml(f)

