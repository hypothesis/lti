# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import urllib
import shutil
import json
import logging
import hashlib

import requests
from pyramid.renderers import render
from pyramid.response import Response

from lti import util
from lti.views import oauth


log = logging.getLogger(__name__)


# pylint: disable = too-many-arguments, too-many-locals
def lti_pdf(request, oauth_consumer_key, lis_outcome_service_url,
            lis_result_sourcedid, course, name, value):
    """
    Return a PDF annotation assignment (HTML response).

    Download the PDF file to be annotated from Canvas's API and save it to a
    cache directory on disk, if the file hasn't been cached already.

    This requires an access token for the Canvas API. If we don't have one then
    kick off an authorization code flow to get one, redirecting the browser to
    Canvas's auth endpoint. We'll end up rendering the annotation assignment
    later, after Canvas directs the browser back to us with an authorization.

    """
    post_data = util.requests.capture_post_data(request)
    file_id = value
    auth_data_svc = request.find_service(name='auth_data')
    try:
        lti_token = auth_data_svc.get_lti_token(oauth_consumer_key)
    except KeyError:
        return util.simple_response("We don't have the Consumer Key %s in our database yet." % oauth_consumer_key)
    canvas_server = auth_data_svc.get_canvas_server(oauth_consumer_key)
    url = '%s/api/v1/courses/%s/files/%s' % (canvas_server, course, file_id)
    md5_obj = hashlib.md5()
    md5_obj.update('%s/%s/%s' % (canvas_server, course, file_id))
    digest = md5_obj.hexdigest()
    path = '%s/%s.pdf' % (request.registry.settings['lti_files_path'], digest)
    log.debug("Path for PDF file in cache is: %s", path)
    if util.filecache.exists_pdf(digest, request.registry.settings) is False:
        log.debug("%s is not already cached", digest)
        sess = requests.Session()
        log.debug("Getting %s metadata from %s", digest, url)
        response = sess.get(url=url, headers={'Authorization': 'Bearer %s' % lti_token})
        if response.status_code == 401:
            return oauth.make_authorization_request(
                request, 'pdf:' + urllib.quote(json.dumps(post_data)),
                refresh=True)
        if response.status_code == 200:
            j = response.json()
            url = j['url']
            log.debug("Downloading %s from %s", digest, url)
            urllib.urlretrieve(url, digest)
            log.debug("Hash of downloaded file is: %s", hash_of_file_contents(digest))
            log.debug("Moving %s to %s", digest, path)
            shutil.move(digest, path)
    else:
        log.debug("%s is already cached", digest)

    log.debug("Hash of cached file is: %s", hash_of_file_contents(path))

    fingerprint = util.pdf.get_fingerprint(digest, request.registry.settings)
    if fingerprint is None:
        pdf_uri = '%s/viewer/web/%s.pdf' % (request.registry.settings['lti_server'], digest)
    else:
        pdf_uri = 'urn:x-pdf:%s' % fingerprint

    return Response(
        render('lti:templates/pdf_assignment.html.jinja2', dict(
               name=name,
               hash=digest,
               oauth_consumer_key=oauth_consumer_key,
               lis_outcome_service_url=lis_outcome_service_url,
               lis_result_sourcedid=lis_result_sourcedid,
               doc_uri=pdf_uri,
               lti_server=request.registry.settings['lti_server'],
               )).encode('utf-8'),
        content_type='text/html',
    )


def hash_of_file_contents(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as file_:
        for chunk in iter(lambda: file_.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
