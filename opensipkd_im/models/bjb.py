import os
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    func,
    )
from ..tools import (
    create_now,
    get_settings,
    )
from . import (
    Base,
    DefaultModel,
    DBSession,
    )
    

class Files(Base, DefaultModel):
    __tablename__ = 'files'
    created     = Column(DateTime(True),
                         nullable=False,
                         server_default=func.current_timestamp())    
    path        = Column(String(256), nullable=False, unique=True)
    name        = Column(String(256), nullable=False) # original filename
    mime        = Column(String(256), nullable=False) # file type
    size        = Column(Integer,     nullable=False) # byte
    user_id     = Column(Integer,     ForeignKey('users.id'))
    description = Column(String(256))

    def fullpath(self):
        settings = get_settings()
        dir_path = os.path.realpath(settings['static_files'])         
        return os.path.join(dir_path, self.path)
        

class Cron(Base, DefaultModel):
    __tablename__ = 'cron'
    created = Column(DateTime(True),
                     nullable=False,
                     server_default=func.current_timestamp())
    job     = Column(String(256), nullable=False) # contoh: invoice_file 1
    user_id = Column(Integer,     ForeignKey('users.id'))    
          
    
class Nasabah(Base, DefaultModel):
    __tablename__ = 'nasabah'
    tgl       = Column(DateTime(True),
                       nullable=False,
                       server_default=func.current_timestamp())
    rekening  = Column(String(16), nullable=False, unique=True)
    nama      = Column(String(64), nullable=False)
    tipe      = Column(String(8),  nullable=False)
    mata_uang = Column(String(3),  nullable=False)
    msisdn    = Column(String(20), nullable=False)
    file_id   = Column(Integer,    ForeignKey('files.id'))

class KantorCabang(Base, DefaultModel):
    __tablename__ = 'kantor_cabang'
    nama = Column(String(64), nullable=False)    
    
class KategoriKredit(Base, DefaultModel):
    __tablename__ = 'kategori_kredit'
    nama = Column(String(64), nullable=False, unique=True)
        
class TipeKredit(Base, DefaultModel):
    __tablename__ = 'tipe_kredit'    
    kode               = Column(String(3),  nullable=False, unique=True)
    nama               = Column(String(64), nullable=False)
    kategori_kredit_id = Column(Integer,
                                ForeignKey('kategori_kredit.id'),
                                nullable=False)


class Tagihan(Base, DefaultModel):
    __tablename__ = 'tagihan'
    tgl              = Column(DateTime(True),
                              nullable=False,
                              server_default=func.current_timestamp())
    kantor_cabang_id = Column(Integer,
                              ForeignKey('kantor_cabang.id'),
                              nullable=False)
    tipe_kredit_id   = Column(Integer,
                              ForeignKey('tipe_kredit.id'),
                              nullable=False)
    deal_ref         = Column(String(16),     nullable=False, unique=True)
    nama             = Column(String(32),     nullable=False) # nama singkat
    jatuh_tempo      = Column(DateTime(True), nullable=False) # jatuh tempo
    tunggakan        = Column(Float,          nullable=False, server_default='0')
    tagihan          = Column(Float,          nullable=False) # tagihan pokok
    total            = Column(Float,          nullable=False)                              
    msisdn           = Column(String(20),     nullable=False)
    jatuh_tempo      = Column(DateTime(True), nullable=False)
    berakhir         = Column(DateTime(True), nullable=False)
    user_id          = Column(Integer, ForeignKey('users.id'), nullable=False)
    pesan_id         = Column(Integer)
    
    def save(self, user_id):
        self.total   = self.tunggakan + self.tagihan
        self.user_id = user_id
        self.tgl     = create_now()
        DBSession.add(self)

    def tgl_tz(self):
        return self.as_timezone('tgl')
            
    def jatuh_tempo_tz(self):
        return self.as_timezone('jatuh_tempo')
        
    def berakhir_tz(self):
        return self.as_timezone('berakhir')
