import os
import sys
from ..tools import get_settings


def is_live(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return
    return True

def get_pid(pidfile):
    try:
        f = open(pidfile,'r')
        pid_int = int(f.read().split()[0])
        f.close()
        return pid_int
    except IOError:
        return
    except ValueError:
        return
    except IndexError:
        return
        
def get_pid_file(pid_name=None):
    if not pid_name:
        pid_name = os.path.split(sys.argv[0])[-1]
        pid_name = os.path.splitext(pid_name)[0]
    settings = get_settings()
    dir_path = settings['session.lock_dir']
    return os.path.join(settings['session.lock_dir'], pid_name)
            
def make_pid(pid_file):
    pid = get_pid(pid_file)
    if pid and is_live(pid):
        msg = 'PID saya {pid} masih ada.'.format(pid=pid)
        print(msg)
        sys.exit()
    pid = os.getpid()
    f = open(pid_file, 'w')
    f.write(str(pid))
    f.close()
    return pid

def one_pid():
    pid_file = get_pid_file()
    make_pid(pid_file)
    return pid_file
    
def mkdir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        
def mkdir_from_filename(filename):
    dir_name = os.path.split(filename)[0]
    mkdir(dir_name)
        
def get_fullpath(filename):
    dir_name = os.path.split(__file__)[0]
    return os.path.join(dir_name, filename)

def create_log(filename):
    logformatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    name = str(randrange(1,99999))
    log = logging.getLogger(name)
    handler = logging.FileHandler(filename)
    handler.setFormatter(logformatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log
