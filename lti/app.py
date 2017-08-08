import urllib
import urlparse
import requests
import re
import logging
import filelock
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.response import FileResponse
from requests_oauthlib import OAuth1

from pyramid.renderers import render

from lti.config import configure
from lti import util
from lti import constants


log = logging.getLogger(__name__)


def bare_response(text):
    r = Response(text.encode('utf-8'))
    r.headers.update({
        'Access-Control-Allow-Origin': '*'
        })
    r.content_type = 'text/plain'
    return r

def page_response(html):
    r = Response(html.encode('utf-8'))
    r.headers.update({
        'Access-Control-Allow-Origin': '*'
        })
    r.content_type = 'text/html'
    return r

def serve_file(path=None, file=None, request=None, content_type=None):
    response = FileResponse('%s/%s' % (path, file),
                            request=request,
                            content_type=content_type)
    return response


@view_config(route_name='config_xml',
             renderer='config.xml.jinja2',
             request_method='GET')
def config_xml(request):
    request.response.content_type = 'text/xml'
    return {
        'launch_url': request.route_url('lti_setup'),
        'resource_selection_url': request.route_url('lti_setup'),
    }


@view_config( route_name='about' )
def about(request):
    return serve_file('.', 'about.html', request, 'text/html')

@view_config( route_name='lti_submit' )
def lti_submit(request, oauth_consumer_key=None, lis_outcome_service_url=None, lis_result_sourcedid=None, export_url=None):
    """
    Called from a student's view of an assignment.

    In theory can be an LTI launch but that's undocumented and did not seem to work. 
    So we use info we send to ourselves from the JS we generate on the assignment page.
    """
    log.info ( 'lti_submit: query: %s' % request.query_string )
    log.info ( 'lti_submit: post: %s' % request.POST )
    oauth_consumer_key = util.requests.get_post_or_query_param(request, constants.OAUTH_CONSUMER_KEY)
    lis_outcome_service_url = util.requests.get_post_or_query_param(request, constants.LIS_OUTCOME_SERVICE_URL)
    lis_result_sourcedid = util.requests.get_post_or_query_param(request, constants.LIS_RESULT_SOURCEDID)
    export_url = util.requests.get_post_or_query_param(request, constants.EXPORT_URL)

    try:
        secret = request.auth_data.get_lti_secret(oauth_consumer_key)   # because the submission must be OAuth1-signed
    except:
        return util.simple_response("We don't have the Consumer Key %s in our database yet." % oauth_consumer_key)

    oauth_client = OAuth1(client_key=oauth_consumer_key, client_secret=secret, signature_method='HMAC-SHA1', signature_type='auth_header', force_include_body=True)
    body = render('lti:templates/submission.xml.jinja2', dict(
        url=export_url,
        sourcedid=lis_result_sourcedid,
    ))
    headers = {'Content-Type': 'application/xml'}
    r = requests.post(url=lis_outcome_service_url, data=body, headers=headers, auth=oauth_client)
    log.info ( 'lti_submit: %s' % r.status_code )
    log.info ( 'lti_submit: %s' % r.text )
    response = None
    if ( r.status_code == 200 ):
        response = 'OK! Assignment successfully submitted.'
    else:
        response = 'Something is wrong. %s %s' % (r.status_code, r.text)        
    return util.simple_response(response)

@view_config( route_name='lti_export' )
def lti_export(request):
    """ 
    Called from Speed Grader, which presents the URL that the student submitted.

    Redirects to a variant of our viewer/export prototype which displays annotations for the
    assignment's PDF or URL, filtered to threads involving the (self-identified) H user, and
    highlighting contributions by that user.
    """
    args = util.requests.get_query_param(request, 'args')  # because canvas swallows & in the submitted pox, we pass an opaque construct and unpack here
    log.info ( 'lti_export: query: %s' % request.query_string )
    parsed_args = urlparse.parse_qs(args)
    user = parsed_args['user'][0]
    uri = parsed_args['uri'][0]
    log.info( 'lti_export user: %s, uri %s' % ( user, uri) )
    export_url = '%s/export/facet.html?facet=uri&mode=documents&search=%s&user=%s' % ( request.registry.settings['lti_server'], urllib.quote(uri), user )
    return HTTPFound(location=export_url)


def lti_credentials_form(settings):
    return render('lti:templates/lti_credentials_form.html.jinja2', dict(
        lti_credentials_url=settings['lti_credentials_url'],
    ))

def cors_response(request, response=None):
    if response is None:
        response = Response()
    request_headers = request.headers['Access-Control-Request-Headers'].lower()
    request_headers = re.findall('\w(?:[-\w]*\w)', request_headers)
    response_headers = ['access-control-allow-origin']
    for req_acoa_header in request_headers:
        if req_acoa_header not in response_headers:
            response_headers.append(req_acoa_header)
    response_headers = ','.join(response_headers)
    response.headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '%s' % response_headers,
        'Access-Control-Allow-Methods': "UPDATE, POST, GET"
        })
    response.status_int = 204
    print ( response.headers )
    return response

@view_config( route_name='lti_credentials' )
def lti_credentials(request):
    """ 
    Receive credentials for path A (key/secret/host) or path B (username.username/token/host)
    """
    if  request.method == 'OPTIONS':
        return cors_response(request)

    credentials = util.requests.get_query_param(request, 'credentials')
    if ( credentials is None ):
      return page_response(lti_credentials_form(request.registry.settings))

    lock = filelock.FileLock("credentials.lock")
    with lock.acquire(timeout = 1):
      with open('credentials.txt', 'a') as f:
        f.write(credentials + '\n')
    return bare_response("<p>Thanks!</p><p>We received:</p><p>%s</p><p>We'll contact you to explain next steps.</p>" % credentials)


@view_config( route_name='lti_serve_pdf' )
def lti_serve_pdf(request):
    if request.referer is not None and 'pdf.worker.js' in request.referer:
        return serve_file(path=constants.FILES_PATH,
                      file=request.matchdict['file'] + '.pdf',
                      request=request,
                      content_type='application/pdf')

    return util.simple_response('You are not logged in to Canvas')

from pyramid.response import Response
from pyramid.static import static_view

def create_app(global_config, **settings):  # pylint: disable=unused-argument
    config = configure(settings=settings)

    config.include('pyramid_jinja2')
    config.include('lti.routes')
    config.include('lti.models')

    pdf_view = static_view('lti:static/pdfjs')
    config.add_view(pdf_view, route_name='catchall_pdf')
    config.add_static_view(name='export', path='lti:static/export')

    config.scan()
    return config.make_wsgi_app()
