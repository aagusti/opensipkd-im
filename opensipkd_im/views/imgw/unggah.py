import os
from ...tools import (
    get_settings,
    Upload,
    file_type,
    )
from ...models import DBSession
from ...models.imgw import (
    Files,
    Cron,
    )


class DbUpload(Upload):
    def __init__(self):
        settings = get_settings()
        dir_path = os.path.realpath(settings['static_files'])
        Upload.__init__(self, dir_path)
        
    def save(self, request, name, parser):
        fullpath = Upload.save(self, request, name)
        msg = 'File {fullpath} sudah disimpan. '\
              'Akan diproses beberapa saat lagi.'
        msg = msg.format(fullpath=fullpath)
        request.session.flash(msg)
		
        row = Files()
        #row.path = fullpath.lstrip(self.dir_path)
        row.path = fullpath[len(self.dir_path)+1:]
        row.name = request.POST[name].filename
        row.size = os.stat(fullpath).st_size
        row.mime = file_type(fullpath)
        row.user_id = request.user.id
        row.description = '{parser} dari {path}'.format(parser=parser,
            path=request.path)
        DBSession.add(row)
        DBSession.flush()  
		
        cron = Cron()
        cron.job = '{parser} {id}'.format(parser=parser, id=row.id)
        cron.user_id = request.user.id
        DBSession.add(cron)
        DBSession.flush()
        return row
