# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging

import requests
from pyramid.response import Response
from pyramid.renderers import render
from pyramid.view import view_config

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
    post_data = util.requests.capture_post_data(request)

    oauth_consumer_key = util.requests.get_post_or_query_param(request, constants.OAUTH_CONSUMER_KEY)
    if oauth_consumer_key is None:
        log.error('oauth_consumer_key cannot be None %s', request.POST)
    oauth_consumer_key = oauth_consumer_key.strip()
    lis_outcome_service_url = util.requests.get_post_or_query_param(request, constants.LIS_OUTCOME_SERVICE_URL)
    lis_result_sourcedid = util.requests.get_post_or_query_param(request, constants.LIS_RESULT_SOURCEDID)

    course = util.requests.get_post_or_query_param(request, constants.CUSTOM_CANVAS_COURSE_ID)
    if course is None:
        return util.simple_response(
            'No course number. Was Privacy set to Public for this '
            'installation of the Hypothesis LTI app? If not please do so (or '
            'ask someone who can to do so).')

    post_data[constants.ASSIGNMENT_TYPE] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_TYPE)
    post_data[constants.ASSIGNMENT_NAME] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_NAME)
    post_data[constants.ASSIGNMENT_VALUE] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_VALUE)

    try:
        lti_token = request.auth_data.get_lti_token(oauth_consumer_key)
    except KeyError:
        response = "We don't have the Consumer Key %s in our database yet." % oauth_consumer_key
        return util.simple_response(response)

    if lti_token is None:
        return oauth.make_authorization_request(request, util.pack_state(post_data))

    sess = requests.Session()  # ensure we have a token before calling lti_pdf or lti_web
    canvas_server = request.auth_data.get_canvas_server(oauth_consumer_key)
    url = '%s/api/v1/courses/%s/files?per_page=100' % (canvas_server, course)
    response = sess.get(url=url, headers={'Authorization': 'Bearer %s' % lti_token})
    if response.status_code == 401:
        return oauth.make_authorization_request(
            request, util.pack_state(post_data), refresh=True)

    assignment_type = post_data[constants.ASSIGNMENT_TYPE]
    assignment_name = post_data[constants.ASSIGNMENT_NAME]
    assignment_value = post_data[constants.ASSIGNMENT_VALUE]

    if assignment_type == 'pdf':
        return pdf.lti_pdf(request,
                           oauth_consumer_key=oauth_consumer_key,
                           lis_outcome_service_url=lis_outcome_service_url,
                           lis_result_sourcedid=lis_result_sourcedid,
                           course=course,
                           name=assignment_name,
                           value=assignment_value)

    if assignment_type == 'web':
        return web.web_response(request.registry.settings,
                                request.auth_data,
                                oauth_consumer_key=oauth_consumer_key,
                                course=course,
                                lis_outcome_service_url=lis_outcome_service_url,
                                lis_result_sourcedid=lis_result_sourcedid,
                                name=assignment_name,
                                value=assignment_value)
