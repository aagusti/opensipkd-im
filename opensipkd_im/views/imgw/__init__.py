import re
import time
import socket
import xmlrpclib
from sqlalchemy import (
    or_,
    not_,
    )
from pyramid.view import view_config
from pyramid_xmlrpc import XMLRPCView    
from pyramid.httpexceptions import HTTPFound
import colander
from deform import (
    Form,
    widget,
    ValidationFailure,
    )
from ...models import DBSession
from ...models.imgw import (
    Agent,
    Modem,
    Produk,
    ModemPengirim,
    SmsOutbox,
    IpMsisdn,
    ImAntrian,
    Conf,
    Modem,
    Pulsa,
    )
from ...models.parser import MraConf
from ...tools import (
    get_msisdn,
    dict_to_str,
    create_datetime,
    create_now,
    )

########
# List #
########
@view_config(route_name='imgw-agent',
             renderer='templates/agent/list.pt',
             permission='imgw-agent')
def view_list(request):
    rows = DBSession.query(Agent).order_by('jalur', 'id')
    count = rows.count()
    return dict(rows=rows,
                 count=count)
    
###########
# Session #
###########
SESS_ADD_FAILED = 'imgw agent add failed'
SESS_EDIT_FAILED = 'imgw agent edit failed'

DB_DRIVER = [ ('postgresql', 'PostgreSQL'),
              ('mysql', 'MySQL'),
              ('mssql+pyodbc', 'MS SQL Server'),
              ('sqlite', 'SQLite') ]

def session_failed(request, session_name):
    r = dict(form=request.session[session_name])
    del request.session[session_name]
    return r
    
def daftar_operator():
    r = []
    for row in DBSession.query(Produk).order_by('nama'):
        r.append(row.nama)
    return r
            
def get_agent_form(request, class_form):
    schema = class_form()
    #schema = class_form(validator=form_validator)
    #schema = schema.bind(daftar_operator=daftar_operator())
    schema = schema.bind(daftar_db_driver=DB_DRIVER)
    schema.request = request
    return Form(schema, buttons=('save', 'cancel'))   
    
def save_agent(values, user, row=None):
    msisdn = get_msisdn(values['msisdn'])
    if not row:
        row = Agent()
        row.id = msisdn
        row.jalur = 1 # Modem
    if not values['url']:
        values['url'] = None
    row.from_dict(values)
    DBSession.add(row)
    DBSession.flush()
    if 'msisdn' in values:
        modem = DBSession.query(Modem).filter_by(imei=row.id).first()
        if modem:
            q_pulsa = DBSession.query(Pulsa).filter_by(msisdn=modem.msisdn)
            pulsa = q_pulsa.first()
        else:
            modem = Modem()
            modem.imei = row.id
            pulsa = None
        modem.msisdn = msisdn
        DBSession.add(modem)
        DBSession.flush()
        terdaftar = []
        base_q = DBSession.query(ModemPengirim).\
                    filter_by(msisdn=values['msisdn'])
        # AS AXIS CERIA ESIA FLEXI FREN HALO HEPI IM3 MENTARI SIMPATI SMART STARONE THREE XL                    
        for produk in values['pengirim_sms'].split():
            produk = produk.upper()
            terdaftar.append(produk)
            mp = base_q.filter_by(produk=produk).first()
            if mp:
                continue
            mp = ModemPengirim()
            mp.produk = produk
            mp.msisdn = values['msisdn']
            DBSession.add(mp)
        if terdaftar:
            for r in base_q.filter(not_(ModemPengirim.produk.in_(terdaftar))):
                base_q.filter_by(produk=r.produk).delete()
        else:
            base_q.delete()
        if 'cek_pulsa' in values:            
            if not pulsa:
                pulsa = Pulsa()
                pulsa.msisdn = values['msisdn']
            pulsa.request = values['cek_pulsa']
            DBSession.add(pulsa)
            DBSession.flush()                
        elif pulsa:
            DBSession.query(Pulsa).filter_by(msisdn=modem.msisdn).delete()
    return row
        
def save_request(values, request, row=None):
    if 'id' in request.matchdict:
        values['id'] = request.matchdict['id']
    row = save_agent(values, request.user, row)
    request.session.flash('%s %s berhasil disimpan.' % (
        row.jalur_ref.nama.title(), row.id))

def route_list(request):
    return HTTPFound(location=request.route_url('imgw-agent'))            
    

########    
# Form #
########    
class EditSchema(colander.Schema):
    id = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            widget=widget.TextInputWidget(readonly=True),
            title='ID')
    jenis = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            widget=widget.TextInputWidget(readonly=True),
            title='Jenis')
    ket = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            title='Keterangan',
            description='Informasi tambahan, misalnya: untuk SMS')
    url = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            title='URL',
            description='URL im-agent atau im-gw forwarder')
                        
    
@colander.deferred
def db_driver_widget(node, kw):
    values = kw.get('daftar_db_driver', kw)
    return widget.SelectWidget(values=values)
    
    
class AddModemSchema(colander.Schema):
    msisdn = colander.SchemaNode(colander.String(),
                title='MSISDN',
                description='Nomor HP SIM card')
    cek_pulsa = colander.SchemaNode(colander.String(),
                    missing=colander.drop,
                    title='Cek pulsa',
                    contoh='*123#')
    pengirim_sms = colander.SchemaNode(colander.String(),
                    missing=colander.drop,
                    title='Pengirim SMS untuk',
                    description='''Sistem akan menggunakan informasi ini untuk
                        menentukan modem mana yang digunakan untuk mengirim SMS
                        bila nomor penerima menggunakan MENTARI (contoh).
                        Tujuannya efisiensi pulsa. Lebih dari satu pisahkan
                        dengan spasi. Contoh: SIMPATI MENTARI XL. Kosongkan
                        bila siap mengirim untuk semua operator''')
    ket = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            title='Keterangan',
            description='Informasi tambahan, misalnya: Ada di Android '\
                        'milik Eko.')
    url = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            title='URL',
            default='http://127.0.0.1:6543/rpc-imgw',
            description='URL im-agent, im-gw forwarder, atau XMLRPC server '\
                        'lainnya')
    radio = colander.SchemaNode(colander.String(),
                missing=colander.drop,
                title='Untuk radio',
                contoh='Nama radio. Kosongkan jika tidak ingin diteruskan ke '\
                       'database lain.')
    db_driver = colander.SchemaNode(colander.String(),
                missing=colander.drop,
                widget=db_driver_widget,
                title='Database driver',
                description='Database driver yang didukung SqlAlchemy')
    db_name = colander.SchemaNode(colander.String(),
                missing=colander.drop,
                title='Database name',
                description='Nama database')
    db_user = colander.SchemaNode(colander.String(),
                missing=colander.drop,
                title='Database user',
                description='Database username')
    db_pass = colander.SchemaNode(colander.String(),
                missing=colander.drop,
                widget=widget.PasswordWidget(),
                title='Database password',
                description='Sengaja tidak ditampilkan untuk keamanan. '\
                        'Jika kosong maka tidak diubah.')
    db_host = colander.SchemaNode(colander.String(),
                missing=colander.drop,
                title='Database host',
                description='IP database server')
    db_port = colander.SchemaNode(colander.String(),
                missing=colander.drop,
                title='Database port',
                description='Database network port. Kosongkan untuk nilai'\
                            'default')
                            

class EditModemSchema(AddModemSchema):
    id = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            widget=widget.TextInputWidget(readonly=True),
            title='ID')


###################
# URL Add Handler #
###################
@view_config(route_name='imgw-agent-add',
             renderer='templates/agent/add.pt',
             permission='imgw-agent-add')
def view_add(request):
    cls = AddModemSchema
    form = get_agent_form(request, cls)
    if request.POST:
        if 'save' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_ADD_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('imgw-agent-add'))
            save_agent(dict(controls), request)
        return route_list(request)
    elif SESS_ADD_FAILED in request.session:
        return session_failed(request, SESS_ADD_FAILED)
    return dict(form=form.render())
                    

####################    
# URL Edit Handler #
####################    
def query_id(request):
    return DBSession.query(Agent).filter_by(id=request.matchdict['id'])
    
def id_not_found(request):    
    msg = 'Agent ID %s not found.' % request.matchdict['id']
    request.session.flash(msg, 'error')
    return route_list(request)
    
@view_config(route_name='imgw-agent-edit',
             renderer='templates/agent/edit.pt',
             permission='imgw-agent-edit')
def view_edit(request):
    row = query_id(request).first()
    if not row:
        return id_not_found(request)
    cls = row.jalur == 1 and EditModemSchema or EditSchema    
    form = get_agent_form(request, cls)
    if request.POST:
        if 'save' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_EDIT_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('imgw-agent-edit',
                                  id=row.id))
            save_agent(dict(controls), request, row)
        return route_list(request)
    elif SESS_EDIT_FAILED in request.session:
        return session_failed(request, SESS_EDIT_FAILED)
    values = row.to_dict()
    values['jenis'] = row.jalur_ref.nama.title()
    if row.modem:
        values['msisdn'] = row.modem.msisdn
        pengirim_sms = []
        for mp in row.modem.reply_for:
            pengirim_sms.append(mp.produk)
        pengirim_sms.sort()
        values['pengirim_sms'] = ' '.join(pengirim_sms)
        if row.modem.pulsa:
            values['cek_pulsa'] = row.modem.pulsa.request
    q_mra_conf = DBSession.query(MraConf).filter_by(agent_id=row.id)
    mra_conf = q_mra_conf.first()
    if mra_conf:
        values['radio'] = mra_conf.radio
        db = mra_conf.get_db_info()
        values['db_driver'] = db['driver']
        values['db_user'] = db['user']
        values['db_host'] = db['host']
        values['db_port'] = db['port']
        values['db_name'] = db['name']        
    values = dict_to_str(values)
    return dict(form=form.render(appstruct=values))
    
##########
# Delete #
##########
@view_config(route_name='imgw-agent-delete',
             renderer='templates/agent/delete.pt',
             permission='imgw-agent-delete')
def view_agent_delete(request):
    q = query_id(request)
    row = q.first()
    if not row:
        return id_not_found(request)
    form = Form(colander.Schema(), buttons=('delete','cancel'))
    if request.POST:
        if 'delete' in request.POST:
            id = row.modem and row.modem.msisdn or row.id
            msg = '%s %s sudah dihapus.' % (row.jalur_ref.nama.title(), id)
            q.delete()
            DBSession.flush()
            request.session.flash(msg)
        return route_list(request)
    return dict(row=row,
                 form=form.render())
                 
###########
# Restart #
###########
@view_config(route_name='imgw-agent-restart',
             permission='imgw-agent')                 
def agent_restart(request):
    agent_id = request.matchdict['id']
    url = agent_url(agent_id)
    p = dict(id = agent_id)
    msg = 'XMLRPC request to {url} method restart parameters {p}.'.format(url=url,
            p=p)
    remote = xmlrpclib.ServerProxy(url)
    try:
        r = remote.restart(p)
        msg = '{s} Response {r}'.format(s=msg, r=r)
        request.session.flash(msg)
    except socket.error, err:
        msg = '{s} Response {r}'.format(s=msg, r=err)
        request.session.flash(msg, 'error')
    return HTTPFound('/imgw/agent')
    
@view_config(route_name='imgw-agent-restart-all',
             permission='imgw-agent')                     
def agent_restart_all(request):
    q = DBSession.query(Agent).distinct(Agent.url)
    for row in q:
        if row.url:
            url = row.url
        else:
            url = agent_default_url()
        p = dict(id='all')
        msg = 'XMLRPC request to {url} method restart parameters {p}.'.format(
                url=url, p=p)
        remote = xmlrpclib.ServerProxy(url)
        try:
            r = remote.restart(p)
            msg = '{s} Response {r}'.format(s=msg, r=r)
            request.session.flash(msg)
        except socket.error, err:
            msg = '{s} Response {r}'.format(s=msg, r=err)
            request.session.flash(msg, 'error')
    return HTTPFound('/imgw/agent')                

def agent_url(agent_id):
    q = DBSession.query(Agent).filter_by(id=agent_id)
    agent = q.first()
    # Agent terpisah dengan im-gw ?
    if agent.url:
        return agent.url
    # Web server beda host dengan im-gw ?
    key = 'url ' + agent.id
    q = DBSession.query(Conf).filter_by(grup='im gw', nama=key)
    row = q.first()
    if row:
        return row.nilai
    return agent_default_url()

def agent_default_url():
    q = DBSession.query(Conf).filter_by(grup='im gw', nama='url')
    row = q.first()
    if row:
        return row.nilai
    q = DBSession.query(Conf).filter_by(grup='im gw', nama='result port')
    row = q.first()
    if row:
        port = int(row.nilai)
    else:
        port = 9317
    return 'http://127.0.0.1:%d' % port
    
#############    
# Cek pulsa #
#############
@view_config(route_name='imgw-agent-cek-pulsa',
             permission='imgw-agent')
def modem_cek_pulsa(request):
    agent_id = request.matchdict['id']
    q = DBSession.query(Modem).filter_by(imei=agent_id)
    modem = q.first()
    q = DBSession.query(Pulsa).filter_by(msisdn=modem.msisdn)
    pulsa = q.first()
    # *123#   -> USSD
    # 999 cek -> SMS
    t = pulsa.request.split()
    try:
        penerima = int(t[0])
    except ValueError:
        penerima = None
    if penerima: # SMS
        penerima = t[0]
        pesan = ' '.join(t[1:])
        msg = '{msisdn} kirim SMS ke {penerima} dengan pesan: {pesan}'.format(
                msisdn=modem.msisdn, penerima=penerima, pesan=pesan)
    else:
        pesan = pulsa.request
        msg = '{msisdn} kirim USSD berisi pesan: {pesan}'.format(
                msisdn=modem.msisdn, pesan=pesan)
    a = ImAntrian(jalur=1, pengirim=modem.msisdn, pesan=pesan)
    if penerima:
        a.penerima = penerima
    DBSession.add(a)
    DBSession.flush()
    request.session.flash(msg)
    return HTTPFound('/imgw/agent')                 
    

###################################################
# Dipanggil oleh aplikasi Android bernama SMSSync #
###################################################
@view_config(route_name='imgw-sms', renderer='json')
def view_sms(request):
    from_ip = request.environ['REMOTE_ADDR']
    q_base = DBSession.query(IpMsisdn)
    q = q_base.filter_by(ip=from_ip)
    penerima = q.first()
    if not penerima:
        q = q_base.filter_by(ip='0.0.0.0')
        penerima = q.first()
        if not penerima:
            message = 'IP %s belum terdaftar' % from_ip
            return {'payload': {
                'success': False,
                'error': message}}
    task = request.params.get('task')
    if task == 'send':
        return smssync_outbox(request)
    if task == 'sent':
        return smssync_sent(request)
    if task == 'results':
        return smssync_delivery_report(request)
    pengirim = request.params.get('from')
    if not pengirim:
        return {
            'payload': {
                'success': True,
                'error': 'Key from tidak ada'}}
    pesan = request.params.get('message')
    tgl_operator = request.params.get('sent_timestamp')
    tgl_operator = float(tgl_operator)/1000 # SMS Gateway Ultimate
    t = time.localtime(tgl_operator)
    tgl_operator = create_datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour,
            t.tm_min, t.tm_sec)
    if pengirim == penerima.msisdn:
        return {
            'payload': {
                'success': True,
                'error': 'Pengirim dan penerima sama, abaikan.'}}
    d = dict(pengirim=pengirim, pesan=pesan, tgl_operator=tgl_operator)
    print('DEBUG inbox: %s' % d)
    ok = pengirim and tgl_operator and pesan is not None and True
    if ok:
        a = ImAntrian()
        a.jalur = 1
        a.kirim = False
        a.pengirim = pengirim
        a.penerima = penerima.msisdn
        a.pesan = pesan
        a.tgl_operator = tgl_operator
        DBSession.add(a)
        DBSession.flush()
        message = 'OK'
    else:
        message = 'Harap sertakan pengirim, pesan, dan tgl_operator.'
    return {
        'payload': {
            'success': True,
            'error': None}}

# Kecepatan modem biasanya 10 detik per SMS. Sementara SMSSync di Android
# membaca task setiap menit. Jadi 60 detik / (10 detik / SMS) = 6 SMS.
def smssync_outbox(request):
    q = DBSession.query(SmsOutbox).order_by('id').limit(6)
    messages = []
    for row in q:
        message = dict(to=row.penerima, message=row.pesan)
        messages.append(message)
        DBSession.query(SmsOutbox).filter_by(id=row.id).delete()        
    if not messages:
        return dict()
    r = {
        'payload': {
            'task': 'send',
            'secret': 'secret',
            'messages': messages,
            }
        }
    print('DEBUG outbox: %s' % r)
    return r

########################################
# XMLRPC Server: menanti kiriman im-gw # 
########################################
class RpcImGw(XMLRPCView):
    def job(self, params):
        a = SmsOutbox(id=params['id'],
                      penerima=params['penerima'],
                      pesan=params['pesan'])
        DBSession.add(a)
        DBSession.flush()
        return dict(status=1, jawaban='Sedang proses', job=0)
    
