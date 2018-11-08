#!/usr/bin/python
# vim: set sw=4 sts=4 et tw=120 :

import json
import logging as log
import requests
import zipfile

class API:
    def __init__(self, client_token=None):
        self.auth_api = 'https://my.remarkable.com'
        self.discovery_api = 'https://service-manager-production-dot-remarkable-production.appspot.com'
        self.storage_api = 'https://document-storage-production-dot-remarkable-production.appspot.com'

        self.client_token = client_token
        self.user_token = None

        if self.client_token:
            self.discovery()
            self.request_user_token()


    def register(self, code, deviceid):
        auth_url = self.auth_api + '/token/device/new'
        auth_data = {
            'code':       code,              # the one-time code
            'deviceDesc': 'desktop-windows',
            'deviceID':   deviceid           # the UUID identifying the client, not the tablet!
        }

        response = requests.post(url = auth_url, json = auth_data)

        self.client_token = response.text
        self.discovery()

    def upload(self,rel_path,blob_uuid,doc_name,doc_path):

        
        payload = [{
            "ID": blob_uuid,
            "Type": "DocumentType",
            "Version": 1
        }]
        upload_request_url =self.storage_api +"/document-storage/json/2/upload/request"

        response = requests.put(url=upload_request_url, data=payload)
        if response.status_code == requests.codes.ok:
            response_dict = json.loads(response.text)
            upload_url = response_dict["BlobURLPut"]
            if response_dict["Success"]:
                print("success for upload request")
                doc_payload,doc_zip = self.prepare_package(doc_uuid,'',doc_name)
                resp_upload =requests.post(upload_url,files= {'body': open(doc_zip,'rb') })
                print (resp_upload.content)
                update_md_url =self.storage_api +"/document-storage/json/2/upload/update-status"
                update_resp = requests.put(update_md_url,doc_payload)
                print (update_resp.content)

            response_up = requests.put(url=upload_url, data=payload)

        
    def prepare_package(self,doc_uuid,parent_uuid ='',doc_name ="ABC"):
        package_json = {
        'ID' :  doc_uuid,
        'Parent' : parent_uuid,
        'VissibleName' : doc_name,
        'ModifiedClient' : utc_time,
        'Type' : "DocumentType",
        'Version' : 1
        }
        zip_name = "{}.zip".format(doc_uuid)
        package_zip = zipfile.ZipFile(zip_name,
                "w", zipfile.ZIP_DEFLATED)
        package_zip.write(doc_uuid + '.pdf')
        package_zip.writestr(doc_uuid + '.pagedata', '')
        with open(doc_uuid+".content","w") as json_fp:
            json.dump({
            'extraMeatadata': [],
            'fileType': 'pdf',
            'lastOpenedPage': 0,
            'lineHeight' : -1,
            'margins' : 100,
            #'pageCount' => 1, # we don't know this, but it seems the reMarkable can count
            'textScale' : 1,
            'transform' : [] # no idea how to fill this, but it seems optional
            },json_fp
            )
        package_zip.write(doc_uuid + '.content')
        package_zip.close()
        return package_json,zip_name

    

    def request_user_token(self):
        update_url = self.auth_api + '/token/user/new'
        update_headers = { 'Authorization' : 'Bearer {}'.format(self.client_token) }

        response = requests.post(url = update_url, headers = update_headers)

        self.user_token = response.text

        return response


    def discovery(self):
        discovery_url = self.discovery_api + '/service/json/1/document-storage'
        discovery_headers = { 'Authorization': 'Bearer {}'.format(self.client_token) }
        discovery_data = {
            'environment' : 'production',
            'group' : 'auth0|5a68dc51cb30df3877a1d7c4', # TODO: taken from RemarkableAPI, comment: what is this?
            'apiVer': 2,
        }

        response = requests.get(url = discovery_url, headers = discovery_headers, params = discovery_data)

        if response.status_code == requests.codes.ok:
            response_dict = json.loads(response.text)
            self.storage_api = 'https://' + response_dict['Host']


    def download(self, blob_uuid, blob_url):
        response = requests.get(blob_url, allow_redirects=True)
        if not response.status_code == requests.codes.ok:
            log.error('Could not download blob {}: status = {}'.format(blob_uuid, response.status_code))

        return response.content


    def list_items(self, with_blob = False):
        list_url = self.storage_api + '/document-storage/json/2/docs'
        list_headers = { 'Authorization': 'Bearer {}'.format(self.user_token) }
        list_data = { 'withBlob': with_blob }

        response = requests.get(url = list_url, headers = list_headers, params = list_data)

        if response.status_code == requests.codes.ok:
            return json.loads(response.text)

        return None
