import os, time, socket
from datetime import datetime, timedelta

from fabric.api import env
from fabric.context_managers import prefix, settings, hide
from fabric.operations import sudo, run

env.hosts = ['deploy@173.255.255.5']
env.root = '/srv'
env.project = 'hello'
env.user_string = "%s@%s" % (env.local_user, socket.gethostname())
    
LOCK_DIR = "/var/run/%(project)s-deploy" % env

# Maximum number of versions to keep on the server, including the current version.
# Previous versions are automatically deleted. Set to a really high number to disable.
MAX_DEPLOYED_VERSIONS = 4

NGINX_CONFIG_FILE = '/etc/nginx/sites-available/%(project)s' % env
SUPERVISOR_CONFIG_FILE = '/etc/supervisor/conf.d/%(project)s.conf' % env

# Directory to use to store the Python virtualenv
VIRTUALENV_DIR = 'python'

################################################################################
# Utility functions
################################################################################        
def pretty_timedelta(delta):
    delta = timedelta(delta.days, delta.seconds)
    return "%s (HH:MM:SS)" % str(delta)
        
def parse_timestamp(version):
    return datetime.strptime(version, "%Y_%m_%d_%H%M%S") if version is not None else None
    
def pip_download_cache():
    "Returns a command prefix which enables the pip download cache."
    return prefix('export PIP_DOWNLOAD_CACHE=/tmp/pip-download-cache')

def virtualenv(virtualenv_root=None):
    """Return an object, which, when used in a 'with' block, allows commands to be run
    in the Python virtualenv environment"""
    virtualenv_root = virtualenv_root or env.virtualenv_root
    
    return prefix('source %s' % os.path.join(virtualenv_root, 'bin', 'activate'))

def restore_file_from_backup(filename, use_sudo=False):
    bak = "%s.bak" % filename
    cmd = "mv %s %s" % (bak, filename)
    
    with settings(warn_only=True):
        with hide('stdout', 'warnings'):
            if use_sudo:
                sudo(cmd)
            else:
                run(cmd)


################################################################################
# Initialization
################################################################################    
def initialize_environment():
    # Construct paths that refer to the version currently being deployed
    env.version = time.strftime('%Y_%m_%d_%H%M%S')
    env.project_root = os.path.join(env.root, env.project, 'versions', env.version)
    env.virtualenv_root = os.path.join(env.project_root, VIRTUALENV_DIR)
    env.django_root = os.path.join(env.project_root, env.project)
    
    # Construct paths that always refer to the current version
    env.current_version = os.path.join(env.root, env.project, 'current')
    env.current_virtualenv = os.path.join(env.current_version, VIRTUALENV_DIR)
    env.current_django = os.path.join(env.current_version, env.project)

