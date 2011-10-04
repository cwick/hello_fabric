import os, time, re
from fabric.api import env
from fabric.contrib.files import upload_template, exists
from fabric.decorators import task
from fabric.operations import run, sudo, local
from fabric.context_managers import prefix, hide, cd
from fabric.contrib.project import rsync_project
from fabric.utils import abort

env.hosts = ['cwick@newton']
env.root = '/home/cwick/projects'
env.project = 'hello'

EXCLUDE_FILES = ["python", "*.pyc", ".git", ".gitignore"]

def pip_download_cache():
    return prefix('export PIP_DOWNLOAD_CACHE=/tmp/pip-download-cache')

def virtualenv():
    """Return an object, which, when used in a 'with' block, allows commands to be run
    in the Python virtualenv environment"""
    return prefix('source %s' % os.path.join(env.virtualenv_root, 'bin', 'activate'))
    
def bootstrap():
    # Construct paths that refer to the version currently being deployed
    virtualenv_dir = 'python'
    env.version = time.strftime('%Y_%m_%d_%H%M%S')
    env.project_root = os.path.join(env.root, env.project, 'versions', env.version)
    env.virtualenv_root = os.path.join(env.project_root, virtualenv_dir)

    # Construct paths that always refer to the current version
    env.current_version = os.path.join(env.root, env.project, 'current')
    env.current_virtualenv = os.path.join(env.current_version, virtualenv_dir)
    
    run('mkdir -p %(project_root)s' % env)    
    rsync_project(local_dir='./', remote_dir=env.project_root, exclude=EXCLUDE_FILES)
    if not exists('%(virtualenv_root)s' % env):
        run('virtualenv --no-site-packages %(virtualenv_root)s' % env)

def install_pip_packages():
    """ Installs dependencies with pip """
    with virtualenv():
        with pip_download_cache():
            with hide('stdout'):
                run('cd %(project_root)s && pip install -r config/requirements.txt' % env)
        

def setup_nginx():
    upload_template(
        'config/nginx.conf' % env,
        '/etc/nginx/sites-available/%(project)s' % env,
        use_sudo=True,
        context=env,
        backup=False
    )
    sudo('ln -sfn ../sites-available/%(project)s /etc/nginx/sites-enabled/%(project)s' % env)

def setup_supervisor():
    upload_template(
        'config/supervisor.conf' % env,
        '/etc/supervisor/conf.d/%(project)s.conf' % env,
        use_sudo=True,
        context=env,
        backup=False
    )

def reload_site():
    sudo('service nginx reload')
    sudo('supervisorctl reload')

def set_current_version(version=None):
    """Create a symlink to the given version, or use the version currently being deployed
    if none given."""
    version = version or env.version
    with cd('%(root)s/%(project)s' % env):
        run('ln -sfn versions/%s current' % version)

def get_version_list():
    return run('ls -1t %(root)s/%(project)s/versions' % env).split('\r\n')

@task
def rollback(version=None):
    "Rollback to the specified version"
    with hide("stdout", "running"):
        version_list = get_version_list()
        if len(version_list) == 0:
            abort("Nothing deployed yet, so can't rollback")
            
        if not version:
            if len(version_list) < 2:
                abort("No previous version to roll back to")
            else:
                version = version_list[1]
        elif version == "current":
            version = version_list[0]
        else:
            if version not in version_list:
                abort("Invalid version %s. Try the 'version_list' command" % version)
        
    set_current_version(version_list[1])
    reload_site()

def get_current_version():
    "Get the currently deployed version"
    with hide("everything"):
        cmd = "file %(root)s/%(project)s/current" % env
        match = re.search(r'([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{6})', run(cmd))
        if match:
            return match.groups()[0]
        else:
            return None

@task
def version_list():
    "Print versions available on the server."
    from fabric.colors import green
    current_version = get_current_version()
    with hide("everything"):
        for v in get_version_list():
            if v == current_version:
                print(green(v))
            else:
                print v
@task
def deploy():
    "Deploy code to the server"
    bootstrap()
    install_pip_packages()
    setup_nginx()
    setup_supervisor()
    set_current_version()
    reload_site()

@task
def setup_local():
    "Bootstrap the local development environment"
    local('virtualenv --no-site-packages python')
    local('pip install -E python -r config/requirements.txt')


