# Python 2.7 and 3+ Version

# To support print as a function in Python 2.6+
from __future__ import print_function

try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import urllib
import requests
import base64
from datetime import datetime
import os

# Definitions
HOST = "ops.epo.org"
AUTH_URL = "https://ops.epo.org/3.1/auth/accesstoken"

def check_list(listvar):
    if not isinstance(listvar, list):
        listvar = [listvar]
    return listvar
    
def safeget(dct, *keys):
    """ Recursive function to safely access nested dicts or return None. 
    param dict dct: dictionary to process
    param string keys: one or more keys"""
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct

def keysearch(d, key):
    """Recursive function to look for first occurence of key in multi-level dict. 
    param dict d: dictionary to process
    param string key: key to locate"""
 
    if isinstance(d, dict):
        if key in d:
            return d[key]
        else:
            if isinstance(d, dict):
                for k in d:
                    found = keysearch(d[k], key)
                    if found:
                        return found
            else:
                if isinstance(d, list):
                    for i in d:
                        found = keysearch(d[k], key)
                        if found:
                            return found


class EPOops():
    
    def __init__(self):
        #Load Settings
        parser = configparser.SafeConfigParser()
        parser.read(os.path.abspath(os.path.dirname(__file__)) + '/config.ini')
        self.consumer_key = parser.get('Login Parameters', 'C_KEY')
        self.consumer_secret = parser.get('Login Parameters', 'C_SECRET')
        self.host = HOST
        self.auth_url = AUTH_URL
        self.authorise()
    
    def authorise(self):
        string_to_encode = ":".join([self.consumer_key, self.consumer_secret])
        b64string = base64.b64encode(string_to_encode.encode())
        try:
            # For Python 3>
            params = urllib.parse.urlencode({'grant_type' : 'client_credentials'})
        except AttributeError:
            # If Python < 3
            params = urllib.urlencode({'grant_type' : 'client_credentials'})
        headers = {
            "Authorization" : "Basic %s" % b64string.decode('utf-8'),
            "Accept" : "application/json",
            "Accept-Encoding": "utf-8",
            "Content-Type":"application/x-www-form-urlencoded;charset=UTF-8",
            "Content-Length": "29",
            "Host": self.host,
            "User-Agent": "Python urllib"
        } 
        r = requests.post(self.auth_url, headers=headers, data=params)
        try:
            self.access_token = r.json()['access_token']
        except:
            print (str(r.status_code))
            print (r.text)
        
    def build_request(self, data_url):
        headers = {
            "Authorization" : "Bearer %s" % self.access_token,
            "Accept" : "application/json",
            "Connection": "Keep-Alive"
            }
            
        url = "".join(["https://ops.epo.org", data_url])
        return url, headers
        
    def make_query(self, url_portion, params=None):
        """Function to make a query and return json or statuscode / text."""
        url, headers = self.build_request(url_portion)
        r = requests.get(url, headers=headers, params=params)
        if r.status_code == 400:
            # Get new access token
            self.authorise()
            # Rebuild headers
            url, headers = self.build_request(url_portion)
            # Repeat request
            r = requests.get(url, headers=headers, params=params)
        if r.status_code == 200:
            return r.status_code, r.json()
        else:
            return r.status_code, r.text
        
    def get_data(self, number, number_type="publication", data_type="biblio"):
        #number = publication or application number in epodoc standard
        #number_type = type of number: "publication" or "application" or "priority"
        #data_type = type of data being requested - multiple types can be requested separated with a comma - select from one of [biblio,abstract,equivalents,fulltext,claims,description,images]
        
        data_url = "".join(["/3.1/rest-services/published-data/", number_type, "/epodoc/", number, "/", data_type])
        
        status_code, response = self.make_query(data_url)
        
        return response
    
    def get_register(self, number, number_type="publication", data_type="biblio"):
        """ Get EP patent register entries. """
        data_url = "".join(["/3.1/rest-services/register/", number_type, "/epodoc/", number, "/", data_type])
        return self.make_query(data_url)

    def get_published_desc(self, publication_number):
        """ Get published description for application if it exists.
        param int publication_number: publication number for application in EPO OPS form"""
        #http://ops.epo.org/3.1/rest-services/published-data/publication/epodoc/EP2197188/description
        number_type = "publication"
        data_type   = "description"
        data_url = "".join(["/3.1/rest-services/published-data/", number_type, "/epodoc/", publication_number, "/", data_type])
        
        status_code, response = self.make_query(data_url)
        
        if status_code == 200:
            result = keysearch(response, 'description')
            if result:
                return "\n".join(r['$'] for r in result['p'])
            else:
                return response
        else:
            return status_code, response

    def get_published_claims(self, publication_number):
        """ Get published claims for a published patent application.
        param int publication number"""
        #In certain cases the claim_text is a single string containing all the claims
        number_type = "publication"
        data_type   = "claims"
        data_url = "".join(["/3.1/rest-services/published-data/", number_type, "/epodoc/", publication_number, "/", data_type])
        
        status_code, response = self.make_query(data_url)
        
        if status_code == 200:
            claim_text = response["ops:world-patent-data"]["ftxt:fulltext-documents"]["ftxt:fulltext-document"]["claims"]["claim"]["claim-text"]
            return claim_text
            
        if status_code == 404:
            #Try claims of PCT publication if no claims for EP publication
            #Get register entry
            status_code, response = self.get_register(publication_number)
            if status_code == 200:
                wo_pub_no = None
                for pub_ref in response["ops:world-patent-data"]["ops:register-search"]["reg:register-documents"]["reg:register-document"]["reg:bibliographic-data"]["reg:publication-reference"]:
                    if pub_ref["reg:document-id"]["reg:country"]["$"] == "WO":
                        wo_pub_no = "".join(["WO", pub_ref["reg:document-id"]["reg:doc-number"]["$"]])
                if wo_pub_no:
                    data_url = "".join(["/3.1/rest-services/published-data/", number_type, "/epodoc/", wo_pub_no, "/", data_type])
                    print(data_url)
                    status_code, response = self.make_query(data_url)
                    if status_code == 200:
                        claim_text = response["ops:world-patent-data"]["ftxt:fulltext-documents"]["ftxt:fulltext-document"]["claims"]["claim"]["claim-text"]
                        return claim_text
            print("Claims not found")
            return None
        else:
            return None
    
    def get_publications(self, epodoc_no):
        # Function to take an epodoc application number and return publication number and date
        pass
    
    def convert_number(self, country_code, application_no, filing_date = None):
        data_url = "/3.1/rest-services/number-service/application/original/"
        request_type = "/epodoc" #choice of this or docdb
        if filing_date:
            # Need to use strftime on filing date
            data_url = data_url + country_code + ".(" + application_no + ")." + filing_date + request_type
        else:
            data_url = data_url + country_code + ".(" + application_no + ")" + request_type
        
        status_code, response = self.make_query(data_url)
        
        if status_code == 200:
            doc_no = response["ops:world-patent-data"]["ops:standardization"]["ops:output"]["ops:application-reference"]["document-id"]["doc-number"]["$"]
        else:
            doc_no = None
        return doc_no
        
    def clean_data(self, data):
        """ Flatten data structure holding key patent information.
        param dict data: dictionary from parsed JSON"""
        
        cleaned_data = {}
        
        # Check data relates to located document
        data_to_check = safeget(data, "ops:world-patent-data", "exchange-documents", "exchange-document")
        if isinstance(data_to_check, dict):
            if data_to_check.get("@status") == "not found":
                return "Error: document not found"
            else:
                exdoc = data_to_check
        else:
            if isinstance(data_to_check, list) and (len(data_to_check) > 0):
                exdoc = data_to_check[0]
            else:
                return "Error: document not found"
              
        title_list = check_list(safeget(exdoc, "bibliographic-data", "invention-title"))
        cleaned_data["title"] = [title.get("$", None) for title in title_list if title.get("@lang", None) == "en"][0]
          
        publication = check_list(safeget(exdoc, "bibliographic-data", "publication-reference", "document-id"))
    
        cleaned_data["publication"] = [
            {
                "number": safeget(pub_record, "doc-number", "$"), 
                "date": safeget(pub_record, "date", "$")
            } for pub_record in publication if (pub_record.get("@document-id-type", None) == "epodoc")]
                  
        cleaned_data["applicants"] = [safeget(applicant, "applicant-name", "name", "$") for applicant in safeget(exdoc, "bibliographic-data", "parties", "applicants", "applicant") if applicant.get("@data-format", None) == "epodoc"]
            
        cleaned_data["inventors"] = [safeget(inventor, "inventor-name", "name", "$") for inventor in safeget(exdoc, "bibliographic-data", "parties", "inventors", "inventor") if inventor.get("@data-format", None) == "epodoc"]
        
        cleaned_data["application"] = [{"number": safeget(appln_record, "doc-number", "$"), "date": safeget(appln_record, "date", "$")} for appln_record in safeget(exdoc, "bibliographic-data", "application-reference", "document-id") if appln_record.get("@document-id-type", None) == "epodoc"]
        
        priority_list = check_list(safeget(exdoc, "bibliographic-data", "priority-claims", "priority-claim"))
        cleaned_data["priorityclaims"] = []
        for priority in priority_list:
            for p_record in check_list(priority.get("document-id", None)):
                if p_record.get("@document-id-type", None) == "epodoc":
                    cleaned_data["priorityclaims"].append({"number": safeget(p_record, "doc-number", "$"), "date": safeget(p_record, "date", "$")})
        
        cleaned_data["classifications"] = [
        {
            "section" : safeget(classification, "section", "$"), 
            "class" : safeget(classification, "class", "$") ,
            "subclass" : safeget(classification, "subclass", "$"),
            "maingroup": safeget(classification, "main-group", "$"),
            "subgroup" : safeget(classification, "subgroup", "$")
        } for classification in safeget(exdoc, "bibliographic-data", "patent-classifications", "patent-classification")]
        
        cleaned_data["abstract"] = safeget(exdoc, "abstract", "p", "$")
        
        cleaned_data["citations"] = []
        pub_list = []
        for document in check_list(data_to_check):
            if "references-cited" in document.get("bibliographic-data", None):
                citation_list = check_list(safeget(document, "bibliographic-data", "references-cited", "citation"))
                for citation in citation_list:
                    for c_record in check_list(safeget(citation, "patcit", "document-id")):
                        if c_record:
                            if (c_record.get("@document-id-type", None) == "epodoc") and (safeget(c_record, "doc-number", "$") not in pub_list):
                                cleaned_citation = {}
                                cleaned_citation["number"] = safeget(c_record, "doc-number", "$")
                                pub_list.append(safeget(c_record,"doc-number","$"))
                                if "date" in c_record:
                                    cleaned_citation["date"] = safeget(c_record, "date", "$")
                                if "category" in citation:
                                    cleaned_citation["category"] = safeget(citation, "category", "$")
                                cleaned_data["citations"].append(cleaned_citation)            
        
        return cleaned_data
    
    def get_earliestdate(self, clean_data):
        #Gets an earliest effective date, e.g. first priority or application date, from data cleaned with the method above
        appln_dates = [datetime.strptime(appln["date"],"%Y%m%d") for appln in clean_data["application"]]
        priority_dates = [datetime.strptime(priority["date"],"%Y%m%d") for priority in clean_data["priorityclaims"]]
        date_list = appln_dates + priority_dates
        earliest = min(date_list)
        return earliest

