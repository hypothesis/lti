# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import requests
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render

from lti import util
from lti import constants
from lti.views import oauth


@view_config(route_name='resource_selection')
def resource_selection(request):
    """Respond to an LTI resource selection request."""
    oauth_consumer_key = util.requests.get_post_or_query_param(request, constants.OAUTH_CONSUMER_KEY)
    if oauth_consumer_key is None:
        log.error('oauth_consumer_key cannot be None %s', request.POST)
    oauth_consumer_key = oauth_consumer_key.strip()

    try:
        lti_token = request.auth_data.get_lti_token(oauth_consumer_key)
    except KeyError:
        response = "We don't have the Consumer Key %s in our database yet." % oauth_consumer_key
        return util.simple_response(response)

    course = util.requests.get_post_or_query_param(request, constants.CUSTOM_CANVAS_COURSE_ID)

    if course is None:
        return util.simple_response(
            'No course number. Was Privacy set to Public for this '
            'installation of the Hypothesis LTI app? If not please do so (or '
            'ask someone who can to do so).')

    return_url = util.requests.get_post_or_query_param(request, constants.EXT_CONTENT_RETURN_URL)
    if return_url is None:  # this is an oauth redirect so get what we sent ourselves
        return_url = util.requests.get_post_or_query_param(request, 'return_url')

    target_link_uri = request.route_url('resource_selection', _query={
        constants.CUSTOM_CANVAS_COURSE_ID: course,
        constants.OAUTH_CONSUMER_KEY: oauth_consumer_key,
        constants.EXT_CONTENT_RETURN_URL: return_url,
    })

    if lti_token is None:
        return oauth.make_authorization_request(
            request, target_link_uri, oauth_consumer_key)

    try:
        files = get_pdf_files(
            request.auth_data.get_canvas_server(oauth_consumer_key),
            course,
            lti_token)
    except APIError:
        return oauth.make_authorization_request(
            request, target_link_uri, oauth_consumer_key, refresh=True)

    pdf_choices = ''
    if files:
        pdf_choices += '<ul>'
        for pdf_file in files:
            file_id = str(pdf_file['id'])
            name = pdf_file['display_name']
            if not name.lower().endswith('.pdf'):
                continue
            pdf_choices += '<li><input type="radio" name="pdf_choice" onclick="javascript:go()" value="%s" id="%s">%s</li>' % (name, file_id, name) 
        pdf_choices += '</ul>'

    launch_url_template = (
        '%s/lti_setup?assignment_type=__TYPE__&assignment_name=__NAME__'
        '&assignment_value=__VALUE__&return_url=__RETURN_URL__' % request.registry.settings['lti_server'])

    return Response(render('lti:templates/document_chooser.html.jinja2', dict(
        return_url=return_url,
        launch_url=launch_url_template,
        pdf_choices=pdf_choices,
    )))


def get_pdf_files(canvas_server, course, lti_token):
    """
    Return the list of PDF files that have been uploaded to the course.

    This sends possibly multiple synchronous network requests to the Canvas
    API.

    """
    sess = requests.Session()
    sess.headers['Authorization'] = 'Bearer {token}'.format(token=lti_token)

    def get(url):
        response = sess.get(url)
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            raise APIError(err)
        return response

    # Get the first page of the list of files.
    response = get('{server}/api/v1/courses/{course}/files?per_page=100'.format(
        server=canvas_server, course=course))

    files = response.json()

    # Get any further pages of the list of files.
    while 'next' in response.links:
        files.extend(get(response.links['next']['url']).json())

    return files


def packed_state(request):
    post_data = util.requests.capture_post_data(request)
    post_data[constants.ASSIGNMENT_TYPE] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_TYPE)
    post_data[constants.ASSIGNMENT_NAME] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_NAME)
    post_data[constants.ASSIGNMENT_VALUE] = util.requests.get_post_or_query_param(request, constants.ASSIGNMENT_VALUE)
    return util.pack_state(post_data)


class APIError(Exception):
    pass
