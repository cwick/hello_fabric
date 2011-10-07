from fabric.api import env
from fabric.context_managers import cd
from fabric.decorators import task
from fabric.operations import run, sudo

from .common import virtualenv, initialize_environment

################################################################################
# Task definitions
################################################################################    
@task
def syncdb():
    "Run the syncdb django management command"
    initialize_environment()
    with virtualenv(env.current_virtualenv):
        with cd("%(current_django)s" % env):
            run("python manage.py syncdb")

@task
def create():
    "Create the application database"
    sudo("createdb %(project)s" % env, user="postgres")