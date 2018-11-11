#! /usr/bin/env python
import os
from flask import Flask, redirect, render_template, request, session
import yaml
import uuid
import zipfile
import urllib
#from urlparse import  urlparse as urlparse
from mendeley import Mendeley
from mendeley.session import MendeleySession
from syncrm import cli 
from argparse import Namespace
from os.path import join as osp
from os.path import dirname as dirname
with open(osp(dirname(__file__),'config.yml'),'r') as f:
    config = yaml.load(f)

REDIRECT_URI = 'http://localhost:5000/oauth'

app = Flask(__name__)
app.debug = True
app.secret_key = config['clientSecret']

mendeley = Mendeley(config['clientId'], config['clientSecret'], REDIRECT_URI)


@app.route('/')
def home():
    if 'token' in session:
        return redirect('/listDocuments')

    auth = mendeley.start_authorization_code_flow()
    session['state'] = auth.state

    return render_template('home.html', login_url=(auth.get_login_url()))


@app.route('/oauth')
def auth_return():
    auth = mendeley.start_authorization_code_flow(state=session['state'])
    mendeley_session = auth.authenticate(request.url)

    session.clear()
    session['token'] = mendeley_session.token

    return redirect('/listDocuments')


@app.route('/listDocuments')
def list_documents():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    name = mendeley_session.profiles.me.display_name
    docs = mendeley_session.documents.list(view='client').items

    return render_template('library.html', name=name, docs=docs)


@app.route('/document')
def get_document():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    document_id = request.args.get('document_id')
    doc = mendeley_session.documents.get(document_id)

    return render_template('metadata.html', doc=doc)


@app.route('/metadataLookup')
def metadata_lookup():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    doi = request.args.get('doi')
    doc = mendeley_session.catalog.by_identifier(doi=doi)

    return render_template('metadata.html', doc=doc)


@app.route('/download')
def download():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    document_id = request.args.get('document_id')
    doc = mendeley_session.documents.get(document_id)
    doc_file = doc.files.list().items[0]

    return redirect(doc_file.download_url)


@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect('/')


def get_session_from_cookies():
    return MendeleySession(mendeley, session['token'])

@app.route('/initrepo')
def init_remarkable():
    cli.init(Namespace(**{
        'DIRECTORY': "RemarkableTablet",
        'ONE_TIME_CODE' : config["OneTimeCode"],
        'verbose': True
        })
    )

@app.route('/checkout_rm')
def checkout_remarkable():
    cli.checkout(Namespace(**{
        'verbose': True
        }))
    
@app.route('/singlepdfupload')
def push_remarkable(pdf_file) :
    doc_uuid = str(uuid.uuid4())
    fname = os.path.basename(pdf_file)
    cli.push(pdf_file,doc_uuid,fname)


@app.route('/download')
def copytotablet():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    document_id = request.args.get('document_id')
    doc = mendeley_session.documents.get(document_id)
    doc_file = doc.files.list().items[0]
    z = redirect(doc_file.download_url)
    doc_uuid = str(uuid.uuid4())
    url_resp = urllib.parse.urlparse(doc_file.download_url)
    pdf_file = url_resp['path']
    fname = os.path.basename(pdf_file)
    return cli.push_remarkable(fname)


if __name__ == '__main__':
    app.run()