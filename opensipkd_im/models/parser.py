import os
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    SmallInteger,
    BigInteger,
    func,
    )
from sqlalchemy.orm import (
    relationship,
    backref,
    )
from ..tools import (
    create_now,
    get_settings,
    )
from . import (
    Base,
    CommonModel,
    DefaultModel,
    DBSession,
    )
from .tools import (
    extract_db_url,
    create_db_url,
    )


#############
# MRA Radio #
#############
class MraConf(Base, CommonModel):
    __tablename__ = 'mra_conf'
    agent_id = Column(String(64),
                ForeignKey('im.agent.id', ondelete='CASCADE'),
                primary_key=True)
    db_url = Column(String(256), nullable=False)
    radio = Column(String(32), nullable=False)

    def get_db_info(self):
        return extract_db_url(self.db_url)

    def set_db_url(self, p):
        self.db_url = create_db_url(p)
        

class SmsCmd(Base, DefaultModel):
    __tablename__ = 'smscmd'
    field01 = Column(String(160)) #cmd
    field02 = Column(String(160)) #Success Message
    field03 = Column(String(160)) #Wrong Message
    field04 = Column(String(160)) #Allowed Receiver
    field05 = Column(String(165)) #Unique field
    field06 = Column(String(165)) #Unique Message
    field07 = Column(SmallInteger) #Number of Content
    field08 = Column(SmallInteger) #Status Active Default 1
  
        
class SmsParsed(Base, DefaultModel):
    __tablename__ = 'smsparsed'
    field01 = Column(DateTime(True),
                         nullable=False,
                         server_default=func.current_timestamp())  
    field00 = Column(String(160)) #receiver
    field02 = Column(String(160)) #sender
    field03 = Column(String(160)) #cmd
    field04 = Column(String(160))
    field05 = Column(String(160))
    field06 = Column(String(160))
    field07 = Column(String(160))
    field08 = Column(String(160))
    field09 = Column(String(160))
    field10 = Column(String(160))
    field11 = Column(SmallInteger) # Status Process
  
  
class SmsWinner(Base, DefaultModel):
    __tablename__ = 'smswinner'
    field01 = Column(DateTime(True),
                         nullable=False,
                         server_default=func.current_timestamp())  
    smsparsed_id = Column(BigInteger, ForeignKey("smsparsed.id"))
    field02 = Column(String(160))
    field03 = Column(String(160))
    smsparsed = relationship(SmsParsed, backref=backref('smswinner'))
    field04 = Column(SmallInteger, nullable=False, default=0)
    
    #relationship('ModemPengirim', backref='im.modem_pengirim', order_by='ModemPengirim.produk') 
    
