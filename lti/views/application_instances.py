
from pyramid.view import view_config
from pyramid.response import Response

from pyramid.renderers import render
from lti.models import application_instance as ai

@view_config(route_name='welcome', request_method='POST', renderer='lti:templates/application_instances/create_application_instance.html.jinja2')
def create_application_instance(request):
  """
    Creates a new ApplicationInstance if one doesn't already exist for the requested domain.
    If one exists the existing data is provided to view.
  """
  # TODO handle missing scheme in lms_url

  instance = ai.build_from_lms_url(request.params['lms_url'])
  request.db.add(instance)

  return {
    'consumer_key': instance.consumer_key,
    'shared_secret': instance.shared_secret
  }

@view_config(route_name='welcome', renderer="lti:templates/application_instances/new_application_instance.html.jinja2")
def new_application_instance(request):
  """
    Renders the form where users enter the lms url and email
  """
  return {}
