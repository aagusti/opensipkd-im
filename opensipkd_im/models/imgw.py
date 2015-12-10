import pytz
from datetime import (
    datetime,
    timedelta,
    )
from sqlalchemy import (
    Column,
    Integer,
    Float,
    Text,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    Sequence,
    func
    )
from sqlalchemy.orm import relationship
from . import (
    Base,
    DBSession,
    DefaultModel,
    CommonModel,
    )
from ..tools import create_now
    

class Jalur(Base, DefaultModel):
    __tablename__ = 'jalur'
    nama = Column(String(15), unique=True, nullable=False)


class MessageModel(DefaultModel):
    @classmethod
    def create(cls):
        seq = Sequence('antrian_id_seq', schema='im')
        id = seq.execute(DBSession.bind)
        return cls(id=id, tgl=create_now())    


class ImAntrian(Base, MessageModel):
    __tablename__ = 'antrian'
    __table_args__ = dict(schema='im')
    jalur        = Column(Integer, ForeignKey('jalur.id'), nullable=False, default=1)
    kirim        = Column(Boolean, nullable=False, default=True)
    tgl          = Column(DateTime(timezone=True), default=create_now, nullable=False)
    tgl_operator = Column(DateTime(timezone=True), default=create_now)
    pengirim     = Column(String(64))
    penerima     = Column(String(64))
    pesan        = Column(Text, nullable=False)
    jawaban      = Column(Text)
    parser       = Column(String(64))
    status       = Column(Integer, default=1, nullable=False)
        

class ImSelesai(Base, MessageModel):
    __tablename__ = 'selesai'
    __table_args__ = dict(schema='im')
    jalur        = Column(Integer, ForeignKey('jalur.id'), nullable=False, default=1)
    kirim        = Column(Boolean, nullable=False)
    tgl          = Column(DateTime(timezone=True), default=create_now, nullable=False)
    tgl_operator = Column(DateTime(timezone=True))
    pengirim     = Column(String(64))
    penerima     = Column(String(64))
    pesan        = Column(Text, nullable=False)
    jawaban      = Column(Text)
    parser       = Column(String(64))
    status       = Column(Integer, default=1, nullable=False)
    
    def tgl_tz(self):
        return self.as_timezone('tgl')
        
    def tgl_operator_tz(self):
        return self.as_timezone('tgl_operator')


class Status(Base, DefaultModel):
    __tablename__ = 'status'
    __table_args__ = dict(schema='im')
    ket = Column(String(100), unique=True)
    

#########
# Agent #
#########
class StatusAgent(Base, DefaultModel):
    __tablename__ = 'status_agent'
    __table_args__ = dict(schema='im')
    ket = Column(String(100), unique=True)
    
class Agent(Base, CommonModel):
    __tablename__ = 'agent'
    __table_args__ = dict(schema='im')
    id         = Column(String(64), primary_key=True)
    jalur      = Column(Integer, ForeignKey('jalur.id'),           nullable=False)
    status     = Column(Integer, ForeignKey('im.status_agent.id'), nullable=False, server_default='0')
    job        = Column(Integer, nullable=False, server_default='0')
    lastjob    = Column(DateTime(timezone=True),
                        nullable=False,
                        default=create_now)
    startup    = Column(DateTime(timezone=True),
                        nullable=False,
                        default=create_now)
    ket        = Column(Text)
    lasterr    = Column(Text)
    url        = Column(String(64))
    urutan_pengirim = Column(Integer)
	
    jalur_ref  = relationship('Jalur',       foreign_keys='Agent.jalur')
    status_ref = relationship('StatusAgent', foreign_keys='Agent.status')
    modem      = relationship('Modem', backref='im.agent', uselist=False)
    
    def lastjob_tz(self):
        return self.as_timezone('lastjob')
        
    def startup_tz(self):
        return self.as_timezone('startup')
        
    def is_new_startup(self):
        return create_now() - self.startup < timedelta(1.0/24)
        
    def is_new_lastjob(self):
        return create_now() - self.lastjob < timedelta(1.0/24)                
        
    def is_timeout(self):
        return self.status == 0 and self.job > 0 and \
            create_now() - self.lastjob > 300
            
            
class Modem(Base, CommonModel):
    __tablename__ = 'modem'
    __table_args__ = dict(schema='im')
    msisdn  = Column(String(64), nullable=False, primary_key=True)
    imei    = Column(String(64), ForeignKey('im.agent.id'), nullable=False)
    produk  = Column(String(20), ForeignKey('produk.nama'), nullable=False)
    device  = Column(String(20))
    sn      = Column(String(20))
    merk    = Column(String(64))
    signal  = Column(Integer,    nullable=False, default=0)
    wilayah = Column(String(30))
	
    pulsa     = relationship('Pulsa',         backref='im.modem', uselist=False)  
    reply_for = relationship('ModemPengirim', backref='im.modem_pengirim', order_by='ModemPengirim.produk')  
        

class Pulsa(Base, CommonModel):
    __tablename__ = 'pulsa'
    __table_args__ = dict(schema='im')
    msisdn   = Column(String(20),
                      ForeignKey('im.modem.msisdn'),
                      nullable=False,
                      primary_key=True)
    request  = Column(String(10), nullable=False)
    response = Column(Text)
    tgl      = Column(DateTime(timezone=True))
    
    def tgl_tz(self):
        return self.as_timezone('tgl')


class Produk(Base, CommonModel):
    __tablename__ = 'produk'
    nama = Column(String(20), nullable=False, primary_key=True)


class ModemPengirim(Base, CommonModel):
    __tablename__ = 'modem_pengirim'
    __table_args__ = dict(schema='im')
    produk        = Column(String(20),
                           ForeignKey('produk.nama'),
                           nullable=False,
                           primary_key=True)
    msisdn        = Column(String(20),
                           ForeignKey('im.modem.msisdn'),
                           nullable=False,
                           primary_key=True)
    msisdn_produk = Column(String(20),
                           ForeignKey('produk.nama'),
                           nullable=False)


class MsisdnPrefix(Base, CommonModel):
    __tablename__ = 'msisdn'
    awalan  = Column(String(10), primary_key=True)
    produk  = Column(String(20), ForeignKey('produk.nama'), nullable=False)
    wilayah = Column(String(30))


class Imei(Base, CommonModel):
    __tablename__ = 'imei'
    __table_args__ = dict(schema='im')
    prefix = Column(String(10), primary_key=True)
    produk = Column(String(20), ForeignKey('produk.nama'), nullable=False)


#########################################
# Untuk Asynchronous sebagai web server #
#########################################
class SmsOutbox(Base, DefaultModel):
    __tablename__ = 'sms_outbox'
    tgl      = Column(DateTime(timezone=True),
                      default=create_now,
                      nullable=False)
    penerima = Column(String(64), nullable=False)
    pesan    = Column(Text,       nullable=False)
 
class IpMsisdn(Base, CommonModel):
    __tablename__ = 'ip_msisdn'
    ip     = Column(String(15), nullable=False, primary_key=True)
    msisdn = Column(String(20), nullable=False)

#################    
# Configuration #
#################    
class Conf(Base, CommonModel):
    __tablename__ = 'conf'
    grup  = Column(String(64), nullable=False, primary_key=True)
    nama  = Column(String(64), nullable=False, primary_key=True)
    nilai = Column(Text,       nullable=False)
    ket   = Column(Text)

######################################
# Broadcast                          #
# Struktur sesuai paket im-broadcast #
######################################
class Broadcast(Base, DefaultModel):
    __tablename__ = 'broadcast'
    __table_args__ = dict(schema='im')    
    tgl      = Column(DateTime(timezone=True), nullable=False, default=create_now)
    judul    = Column(String(64), nullable=False)
    pesan    = Column(Text)
    pengirim = Column(Text)
    admin    = Column(String(64))
    jml      = Column(Integer, nullable=False, default=0)
    
    def tgl_tz(self):
        return self.as_timezone('tgl')
    

class BroadcastPenerima(Base, DefaultModel):
    __tablename__ = 'broadcast_penerima'
    __table_args__ = dict(schema='im')
    pid      = Column(Integer, primary_key=True)
    id       = Column(Integer, ForeignKey('im.broadcast.id'), nullable=False)
    jalur    = Column(Integer, ForeignKey('jalur.id'),        nullable=False, default=1)
    penerima = Column(String(64), nullable=False)
    pesan    = Column(Text)
    nama     = Column(String(64))
    te       = Column(Integer)
    status   = Column(Integer, ForeignKey('im.status.id'),    nullable=False, default=1)
    urutan   = Column(Integer)

########################
# Mail                 #
# Sesuai paket im-mail #
########################
class Mail(Base, CommonModel):
    __tablename__ = 'mail'
    __table_args__ = dict(schema='im')
    id      = Column(Integer,    primary_key=True)
    subject = Column(String(64), nullable=False, default='')
    name    = Column(String(64), nullable=False, default='')


class MailFiles(Base, CommonModel):
    __tablename__ = 'mail_files'
    __table_args__ = dict(schema='im')
    id       = Column(Integer,    nullable=False, primary_key=True)
    urutan   = Column(Integer,    nullable=False)
    filename = Column(String(64), nullable=False, primary_key=True)
    content  = Column(Text,       nullable=False)


########################
# File                 #
# Untuk Upload         #
########################
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
          
        
