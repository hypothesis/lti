# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from pyramid.view import view_config

import logging
import traceback

import requests
from pyramid.response import Response
from pyramid.renderers import render

from lti import constants
from lti import util
from lti.views import oauth
from lti.views import web
from lti.views import pdf


log = logging.getLogger(__name__)


@view_config(route_name='lti_setup')
def lti_setup(request):
    """
    LTI-launched from a Canvas assignment's Find interaction to present choice
    of doc (PDF or URL) to annotate.
  
    LTI-launched again when the Canvas assignment opens.
  
    In those two cases we have LTI params in the HTTP POST -- if we have a
    Canvas API token.

    If there is no token, or the token is expired, called instead by way of
    OAuth redirect. 
    In that case we expect params in the query string.
    """
    log.info ('lti_setup: query: %s' % request.query_string)
    log.info ('lti_setup: post: %s' % request.POST)
    post_data = util.requests.capture_post_data(request)

    oauth_consumer_key = util.requests.get_post_or_query_param(request, constants.OAUTH_CONSUMER_KEY)
    if oauth_consumer_key is None:
        log.error('oauth_consumer_key cannot be None %s' % request.POST)
    oauth_consumer_key = oauth_consumer_key.strip()
    lis_outcome_service_url = util.requests.get_post_or_query_param(request, constants.LIS_OUTCOME_SERVICE_URL)
    lis_result_sourcedid = util.requests.get_post_or_query_param(request, constants.LIS_RESULT_SOURCEDID)

    course = util.requests.get_post_or_query_param(request, constants.CUSTOM_CANVAS_COURSE_ID)
    if course is None:
        log.error('course cannot be None')
        return util.simple_response('No course number. Was Privacy set to Public for this installation of the Hypothesis LTI app? If not please do so (or ask someone who can to do so).')
    
    post_data[constants.ASSIGNMENT_TYPE] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_TYPE)
    post_data[constants.ASSIGNMENT_NAME] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_NAME)
    post_data[constants.ASSIGNMENT_VALUE] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_VALUE)

    log.info ('lti_setup: post_data: %s' % post_data)

    try:
        lti_token = request.auth_data.get_lti_token(oauth_consumer_key)
    except:
        response = "We don't have the Consumer Key %s in our database yet." % oauth_consumer_key
        log.error (response)
        log.error (traceback.print_exc())
        return util.simple_response(response)

    if lti_token is None:
        log.info('lti_setup: getting token')
        return oauth.make_authorization_request(request, util.pack_state(post_data))

    sess = requests.Session()  # ensure we have a token before calling lti_pdf or lti_web
    canvas_server = request.auth_data.get_canvas_server(oauth_consumer_key)
    log.info ('canvas_server: %s' % canvas_server)
    url = '%s/api/v1/courses/%s/files?per_page=100' % (canvas_server, course)
    r = sess.get(url=url, headers={'Authorization':'Bearer %s' % lti_token})
    if r.status_code == 401:
      log.info ('lti_setup: refreshing token')
      return oauth.make_authorization_request(
            request, util.pack_state(post_data), refresh=True)
    files = r.json()
    while ('next' in r.links):
        url = r.links['next']['url']
        r = sess.get(url=url, headers={'Authorization':'Bearer %s' % lti_token})
        files = files + r.json()
    log.info ('files: %s' % len(files))

    assignment_type = post_data[constants.ASSIGNMENT_TYPE]
    assignment_name = post_data[constants.ASSIGNMENT_NAME]
    assignment_value = post_data[constants.ASSIGNMENT_VALUE]

    if assignment_type == 'pdf':
        return pdf.lti_pdf(request, oauth_consumer_key=oauth_consumer_key, lis_outcome_service_url=lis_outcome_service_url, lis_result_sourcedid=lis_result_sourcedid, course=course, name=assignment_name, value=assignment_value)

    if assignment_type == 'web':
        return web.web_response(request.registry.settings,
                                request.auth_data,
                                oauth_consumer_key=oauth_consumer_key,
                                course=course,
                                lis_outcome_service_url=lis_outcome_service_url,
                                lis_result_sourcedid=lis_result_sourcedid,
                                name=assignment_name,
                                value=assignment_value)

    return_url = util.requests.get_post_or_query_param(request, constants.EXT_CONTENT_RETURN_URL)
    if return_url is None: # this is an oauth redirect so get what we sent ourselves
        return_url = util.requests.get_post_or_query_param(request, 'return_url')

    log.info ('return_url: %s' % return_url)

    launch_url_template = '%s/lti_setup?assignment_type=__TYPE__&assignment_name=__NAME__&assignment_value=__VALUE__&return_url=__RETURN_URL__' % request.registry.settings['lti_server']

    log.info ('key %s, course %s, token %s' % (oauth_consumer_key, course, lti_token))

    pdf_choices = ''
    if len(files) > 0:
        pdf_choices += '<ul>'
        for file in files:
            id = str(file['id'])
            name = file['display_name']
            if not name.lower().endswith('.pdf'):
                continue
            pdf_choices += '<li><input type="radio" name="pdf_choice" onclick="javascript:go()" value="%s" id="%s">%s</li>' % (name, id, name) 
        pdf_choices += '</ul>'
   
    return Response(render('lti:templates/document_chooser.html.jinja2', dict(
        return_url=return_url,
        launch_url=launch_url_template,
        pdf_choices=pdf_choices,
    )))
