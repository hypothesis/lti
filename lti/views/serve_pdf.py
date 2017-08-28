# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.response import FileResponse

from lti import util


@view_config(route_name='lti_serve_pdf')
def serve_pdf(request):
    if request.referer is not None and 'pdf.worker.js' in request.referer:
        return FileResponse('%s/%s' % (request.registry.settings['lti_files_path'],
                                       request.matchdict['file'] + '.pdf'),
                            request=request,
                            content_type='application/pdf')

    return util.simple_response('You are not logged in to Canvas')
