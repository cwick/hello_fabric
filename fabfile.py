import os
from fabric.api import env
from fabric.contrib.files import upload_template, exists
from fabric.decorators import task
from fabric.operations import run, sudo
from fabric.context_managers import cd, prefix
from fabric.contrib.project import rsync_project

env.hosts = ['cwick@newton']
env.root = '/home/cwick/projects'
env.project = 'hello'
env.project_root = os.path.join(env.root, env.project)
env.virtualenv_root = os.path.join(env.project_root, 'python')

def virtualenv():
    """Return an object, which, when used in a 'with' block, allows commands to be run
    in the Python virtualenv environment"""
    return prefix('source %s' % os.path.join(env.virtualenv_root, 'bin', 'activate'))
    
def bootstrap():
    run('mkdir -p %(project_root)s' % env)    
    rsync_project(local_dir='./', remote_dir=env.project_root, exclude=["python", "*.pyc"])
    if not exists('%(virtualenv_root)s' % env):
        run('virtualenv --no-site-packages %(virtualenv_root)s' % env)

def install_pip_packages():
    """ Installs dependencies with pip """
    with virtualenv():
        with cd(env.project_root):
            run('pip install -r config/requirements.txt')
        

def setup_nginx():
    upload_template(
        'config/nginx.conf' % env,
        '/etc/nginx/sites-available/%(project)s' % env,
        use_sudo=True,
        context=env,
        backup=False
    )
    sudo('ln -sf ../sites-available/%(project)s /etc/nginx/sites-enabled/%(project)s' % env)

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
    
@task
def deploy():
    bootstrap()
    install_pip_packages()
    setup_nginx()
    setup_supervisor()
    reload_site()
