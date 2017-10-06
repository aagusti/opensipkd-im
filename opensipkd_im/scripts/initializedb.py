import os
import sys
import transaction
import subprocess
from sqlalchemy import engine_from_config
from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )
from ..models import (
    init_model,
    DBSession,
    Base,
    )
from ..models.imgw import Agent
from ..models.parser import MraConf
import initial_data


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)

def read_file(filename):
    f = open(filename)
    s = f.read()
    f.close()
    return s

def main(argv=sys.argv):
    def alembic_run(ini_file, url):
        s = read_file(ini_file)
        s = s.replace('{{db_url}}', url)
        f = open('alembic.ini', 'w')
        f.write(s)
        f.close()
        subprocess.call(command)   
        os.remove('alembic.ini')

    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    # Create Ziggurat tables
    bin_path = os.path.split(sys.executable)[0]
    alembic_bin = os.path.join(bin_path, 'alembic') 
    command = (alembic_bin, 'upgrade', 'head')    
    alembic_run('alembic.ini.tpl', settings['sqlalchemy.url'])
    # Insert data
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    init_model()
    Base.metadata.create_all(engine)
    initial_data.insert()
    transaction.commit()
