import re
import time
from uuid import uuid4
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
    )
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
             permission='edit_agent')
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
    schema.request = request
    return Form(schema, buttons=('save', 'cancel'))   
    
def save_agent(values, user, row=None):
    msisdn = get_msisdn(values['msisdn'])
    if not row:
        row = Agent()
        row.id = msisdn
        row.jalur = 1 # Modem
    row.from_dict(values)
    DBSession.add(row)
    if 'msisdn' in values:
        modem = DBSession.query(Modem).filter_by(imei=row.id).first()
        if not modem:
            modem = Modem()
            modem.imei = row.id
        modem.msisdn = msisdn
        DBSession.add(modem)
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
    DBSession.flush()
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
                        
    
class AddModemSchema(colander.Schema):
    msisdn = colander.SchemaNode(colander.String(),
                title='MSISDN',
                description='Nomor HP SIM card')
    url = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            title='URL',
            default='http://127.0.0.1:6543/rpc-imgw',
            description='URL im-agent, im-gw forwarder, atau XMLRPC server lainnya')            
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
            description='Informasi tambahan, misalnya: Ada di Android milik Eko')


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
             permission='edit_agent')
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
             permission='edit_agent')
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
    values = dict_to_str(values)
    return dict(form=form.render(appstruct=values))
    
##########
# Delete #
##########
@view_config(route_name='imgw-agent-delete',
             renderer='templates/agent/delete.pt',
             permission='edit_agent')
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
        #msg_id = str(uuid4())
        #message = dict(to=row.penerima, message=row.pesan,
        #               message_uuid=msg_id)
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
    
