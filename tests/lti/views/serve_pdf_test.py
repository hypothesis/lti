# -*- coding: utf-8 -*-

import pytest

from lti.views import serve_pdf


class TestServePDF(object):
    def test_it_serves_pdf_file(self, pyramid_request, FileResponse):
        serve_pdf.serve_pdf(pyramid_request)

        FileResponse.assert_called_once_with('/var/lib/lti/a_pdf_file.pdf',
                                             request=pyramid_request,
                                             content_type='application/pdf')

    def test_it_does_not_serve_file_when_no_referer(self, pyramid_request, util):
        pyramid_request.referer = None

        returned = serve_pdf.serve_pdf(pyramid_request)

        util.simple_response.assert_called_once_with('You are not logged in to Canvas')
        assert returned == util.simple_response.return_value

    def test_it_does_not_serve_file_when_no_pdf_worker_referer(self, pyramid_request, util):
        pyramid_request.referer = ['referer_1', 'referer_2']

        returned = serve_pdf.serve_pdf(pyramid_request)

        util.simple_response.assert_called_once_with('You are not logged in to Canvas')
        assert returned == util.simple_response.return_value


@pytest.fixture
def pyramid_request(pyramid_request):
    pyramid_request.referer = ['pdf.worker.js']
    pyramid_request.matchdict['file'] = 'a_pdf_file'

    return pyramid_request


@pytest.fixture
def util(patch):
    util = patch('lti.views.serve_pdf.util')
    return util


@pytest.fixture
def FileResponse(patch):
    return patch('lti.views.serve_pdf.FileResponse')
