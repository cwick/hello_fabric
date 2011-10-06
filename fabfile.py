import os, time, re, socket
import StringIO
from datetime import datetime, timedelta

from fabric.api import env
from fabric.colors import red, green
from fabric.contrib.console import confirm
from fabric.contrib.files import upload_template
from fabric.decorators import task, runs_once
from fabric.operations import run, sudo, local, put, get
from fabric.context_managers import prefix, hide, cd, settings
from fabric.utils import abort

env.hosts = ['deploy@173.255.255.5']
env.root = '/srv'
env.project = 'hello'
env.user_string = "%s@%s" % (env.local_user, socket.gethostname())
    
EXCLUDE_FILES = ["python", "*.pyc", ".git", ".gitignore"]
LOCK_DIR = "/var/run/%(project)s-deploy" % env

# Maximum number of versions to keep on the server, including the current version.
# Previous versions are automatically deleted. Set to a really high number to disable.
MAX_DEPLOYED_VERSIONS = 4

NGINX_CONFIG_FILE = '/etc/nginx/sites-available/%(project)s' % env
SUPERVISOR_CONFIG_FILE = '/etc/supervisor/conf.d/%(project)s.conf' % env

################################################################################
# Lock functions
################################################################################        
def acquire_lock():
    with settings(warn_only=True):
        result = sudo("mkdir %s" % LOCK_DIR)
        if result.succeeded:
            sudo("echo %s > %s/user.txt" % (env.user_string, LOCK_DIR))

        return result.succeeded

def release_lock():
    with settings(warn_only=True):
        sudo("rm -rf %s" % LOCK_DIR)

def get_lock_info():
    buf = StringIO.StringIO()
    with hide("running"):
        get("%s/user.txt" % LOCK_DIR, local_path=buf)
        
    return buf.getvalue().strip("\n")
    
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

def virtualenv():
    """Return an object, which, when used in a 'with' block, allows commands to be run
    in the Python virtualenv environment"""
    return prefix('source %s' % os.path.join(env.virtualenv_root, 'bin', 'activate'))

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
# Deploy
################################################################################        
def deploy_app_archive():
    import tempfile
    try:
        print "Creating app bundle..."
        temp = tempfile.NamedTemporaryFile(delete=False)
        temp.write(local("git archive master --format=zip", capture=True))
        temp.close()

        remote_bundle = "%(project_root)s/%(project)s.zip" % env 
        print "Uploading app bundle..."
        put(temp.name, remote_bundle)
        with hide("stdout"):
            run("cd %s && unzip %s" % (env.project_root, remote_bundle))
    finally:
        os.remove(temp.name)
        run("rm -f %s" % remote_bundle)
    
def setup_nginx():
    upload_template(
        'config/nginx.conf' % env,
        '/etc/nginx/sites-available/%(project)s' % env,
        use_sudo=True,
        context=env,
        backup=True
    )
    sudo('ln -sfn ../sites-available/%(project)s /etc/nginx/sites-enabled/%(project)s' % env)

def setup_supervisor():
    upload_template(
        'config/supervisor.conf' % env,
        '/etc/supervisor/conf.d/%(project)s.conf' % env,
        use_sudo=True,
        context=env,
        backup=True
    )

################################################################################
# Initialization
################################################################################    
def confirm_deploy():
    old_timestamp = parse_timestamp(get_current_version())

    message = "Ready to deploy version %s. %s"
    
    if old_timestamp is None:
        message = message % (env.version, "There are no previous versions.")
    else:
        message = message % (env.version, "The last deploy happened %s ago." \
            % pretty_timedelta(datetime.now() - old_timestamp))

    print message
    return confirm("Proceed with deploy?", default=False)
    
def initialize_environment():
    # Construct paths that refer to the version currently being deployed
    virtualenv_dir = 'python'
    env.version = time.strftime('%Y_%m_%d_%H%M%S')
    env.project_root = os.path.join(env.root, env.project, 'versions', env.version)
    env.virtualenv_root = os.path.join(env.project_root, virtualenv_dir)

    # Construct paths that always refer to the current version
    env.current_version = os.path.join(env.root, env.project, 'current')
    env.current_virtualenv = os.path.join(env.current_version, virtualenv_dir)

def bootstrap():
    run('mkdir -p %(project_root)s' % env)
    
def create_python_environment():
    print "Creating Python environment..."
    run('virtualenv --no-site-packages %(virtualenv_root)s' % env)

    with virtualenv():
        with pip_download_cache():
            with hide('stdout'):
                print "Installing dependencies..."
                run('cd %(project_root)s && pip install -r config/requirements.txt' % env)
    
################################################################################
# Version management
################################################################################        
def reload_site():
    print "Reloading services..."
    sudo('service nginx reload')
    sudo('supervisorctl reload')

def get_version_list():
    with hide("everything"):
        return run('ls -1t %(root)s/%(project)s/versions' % env).split('\r\n')

def purge_old_versions():
    "Delete old versions if necessary"
    for v in get_version_list()[MAX_DEPLOYED_VERSIONS:]:
        run('rm -rf %s/%s/versions/%s' % (env.root, env.project, v))
        
def set_current_version(version=None):
    """Create a symlink to the given version, or use the version currently being deployed
    if none given."""
    version = version or env.version
    with cd('%(root)s/%(project)s' % env):
        run('ln -sfn versions/%s current' % version)

def get_current_version():
    "Get the currently deployed version"
    with hide("everything"):
        cmd = "file %(root)s/%(project)s/current" % env
        with settings(warn_only=True):
            match = re.search(r'([0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{6})', run(cmd))
            if match:
                return match.groups()[0]
            else:
                return None

################################################################################
# Cleanup
################################################################################        
@runs_once
def cleanup_server():
    "Cleanup temporary files used during deploy"
    sudo('rm -f %s.bak' % NGINX_CONFIG_FILE)
    sudo('rm -f %s.bak' % SUPERVISOR_CONFIG_FILE)

def recover_from_failed_deploy():
    try:
        print red("Deploy failed. I will now attempt to recover...")
        run('rm -rf %(root)s/%(project)s/versions/%(version)s' % env)
        restore_file_from_backup(NGINX_CONFIG_FILE, use_sudo=True)
        restore_file_from_backup(SUPERVISOR_CONFIG_FILE, use_sudo=True)
        versions = get_version_list()
        if versions:
            set_current_version(versions[0])

        reload_site()
            
        print red("Server should now be in the state it was before the deploy failed.")
        print red("However, you should run a successful deploy to make sure nothing is broken.")
    except:
        print red("An error occured while attempting to clean up the last deploy.")
        print red("The server may be in an inconsistent state. Execute a successful deploy to fix.")    


################################################################################
# Task definitions
################################################################################    
@task
def rollback(version=None):
    "Rollback to a previous version"

    # Gather verion numbers and make sure it's a valid rollback
    with hide("stdout", "running"):
        version_list = get_version_list()        
        if len(version_list) == 0:
            abort("Nothing deployed yet, so can't rollback")

        cur_version = get_current_version()
        if not version:
            # Rollback by one
            next_idx = version_list.index(cur_version) + 1
            if next_idx >= len(version_list):
                abort("You are already at the oldest version")
            else:
                version = version_list[next_idx]
        elif version == "current":
            # Jump to the most recently deployed version
            version = version_list[0]
            if version == cur_version:
                abort("You are already at the most recently deployed version")
        else:
            # Unknown version number
            if version not in version_list:
                abort("Invalid version %s. Try the 'version_list' command" % version)

        if version == cur_version:
            abort("%s is already the active version." % version)

    # Figure out if we're going backwards or forwards in time
    new_timestamp = parse_timestamp(version)
    old_timestamp = parse_timestamp(cur_version)
    delta = abs(old_timestamp - new_timestamp)
    if old_timestamp > new_timestamp:
        age = "older"
    else:
        age = "newer"

    print "Current version is %s" % green(cur_version)
    print "I will rollback to version %s, which is %s by %s" % (version, age, pretty_timedelta(delta))
    
    if confirm("Proceed with rollback?", default=False):
        set_current_version(version)
        reload_site()
        print "Current version is now %s" % version



@task
def version_list():
    "Print versions available on the server."
    current_version = get_current_version()
    with hide("everything"):
        for v in get_version_list():
            if v == current_version:
                print(green(v))
            else:
                print v
@task
def deploy(force=False):
    "Deploy code to the server"
    initialize_environment()
    
    if not confirm_deploy():
        return

    if not force and not acquire_lock():
        abort("%s is already in the process of deploying. Please wait for them to finish." \
            % get_lock_info())
            
    try:
        start_time = datetime.now()
            
        bootstrap()
        deploy_app_archive()        
        create_python_environment()
        setup_nginx()
        setup_supervisor()
        set_current_version()
        reload_site()
    except BaseException, e:
        print e
        recover_from_failed_deploy()
    finally:
        cleanup_server()
        purge_old_versions()

        # Very important that this comes last!
        release_lock()
        
        print "Deploy took %s" % (pretty_timedelta(datetime.now() - start_time))

@task
def setup_local():
    "Bootstrap the local development environment"
    local('virtualenv --no-site-packages python')
    local('pip install -E python -r config/requirements.txt')


