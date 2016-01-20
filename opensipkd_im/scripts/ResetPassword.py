import os
import sys
import transaction
from random import randrange
from sqlalchemy import engine_from_config
from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )
from ..models import (
    DBSession,
    User,
    init_model,
    Base,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <username>\n'
          '(example: "%s development.ini admin")' % (cmd, cmd))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 3:
        usage(argv)
    config_uri = argv[1]
    username = argv[2]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    Base.metadata.bind = engine
    DBSession.configure(bind=engine)
    init_model()    
    q = DBSession.query(User).filter_by(user_name=username)
    user = q.first()
    if not user:
        print('User {name} tidak terdaftar.'.format(name=username))
        return
    new_password = str(randrange(1000,9999))
    user.password = new_password
    DBSession.add(user)
    DBSession.flush()
    transaction.commit()
    print('Password user {name} telah diubah menjadi {p}'.format(
        name=username, p=new_password))
