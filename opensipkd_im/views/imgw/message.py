from datetime import (
    date,
    datetime,
    timedelta,
    )
from sqlalchemy import (
    or_,
    not_,
    )
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
import webhelpers.paginate    
import colander
from deform import (
    Form,
    widget,
    ValidationFailure,
    )
from ...models import (
    DBSession,
    User,
    )
from ...models.imgw import (
    Jalur,
    ImSelesai,
    ImAntrian,
    Agent,
    Modem,
    ModemPengirim,
    )
from ...tools import (
    create_date,
    get_msisdn,
    one_second,
    create_now,
    get_settings,
    date_from_str,
    dict_to_str,
    create_datetime,
    )


########
# List #
########
JENIS_PESAN = [
    ('sms', 'SMS'),
    ('ussd', 'USSD'),
    ('ym', 'YM'),
    ('xmpp', 'XMPP'),
    ('mail', 'Mail'),
    ]
    
ARUS_PESAN = [
    ('0', 'Penerimaan'),
    ('1', 'Pengiriman'),
    ('1 0', 'Pengiriman berhasil'),
    ('1 -1', 'Pengiriman gagal'),
    ('1 1', 'Pengiriman masih proses'),
    ]


def route_list(request, p={}):
    q = dict_to_str(p)
    return HTTPFound(location=request.route_url('imgw-message', _query=q))

def get_filter(request):
    p = dict(awal=date_from_str(request.params['awal']),
             akhir=date_from_str(request.params['akhir']))
    jenis = request.params.get('jenis')
    if jenis:
        p['jenis'] = jenis
    if jenis != 'ussd':
        kirim = request.params.get('kirim')
        if kirim:
            t = kirim.split()
            p['kirim'] = t[0] == '1'
            if t[1:]:
                p['status'] = t[1]
    if 'status' in p:
        p['status'] = int(p['status'])
    else:
        status = request.params.get('status')
        if status:
            p['status'] = int(status)
    identitas = request.params.get('identitas')
    if identitas:
        p['identitas'] = identitas
    pesan = request.params.get('pesan')
    if pesan:
        p['pesan'] = pesan
    return p
    
def get_rows(p):
    d = p['awal']
    awal = create_datetime(d.year, d.month, d.day)
    d = p['akhir'] + timedelta(1)
    akhir = create_datetime(d.year, d.month, d.day)
    rows = ImSelesai.query().\
                     filter(ImSelesai.tgl >= awal).\
                     filter(ImSelesai.tgl < akhir)
    if 'jenis' in p:
        if p['jenis'] in ['sms', 'ussd']:
            rows = rows.filter_by(jalur=1)
            if p['jenis'] == 'ussd':
                rows = rows.filter(ImSelesai.penerima == None)
            else:
                rows = rows.filter(ImSelesai.penerima != None)
        else:
            jalur = Jalur.query().filter(Jalur.nama.ilike(p['jenis'])).first()
            rows = rows.filter_by(jalur=jalur.id)
    if 'kirim' in p:
        rows = rows.filter_by(kirim=p['kirim'])
    if 'status' in p:
        if p['status'] == 0:
            rows = rows.filter(ImSelesai.status == 0)
        elif p['status'] < 0:
            rows = rows.filter(or_(ImSelesai.status < 0,
                                   ImSelesai.status == 4))
        else:
            rows = rows.filter(ImSelesai.status > 0)
    if 'identitas' in p:
        rows = rows.filter(or_(
                    ImSelesai.pengirim.ilike('%' + p['identitas'] + '%'),
                    ImSelesai.penerima.ilike('%' + p['identitas'] + '%')))
    if 'pesan' in p:
        rows = rows.filter(or_(
                    ImSelesai.pesan.ilike('%' + p['pesan'] + '%'),
                    ImSelesai.jawaban.ilike('%' + p['pesan'] + '%')))
    return rows
    
    
@view_config(route_name='imgw-message',
             renderer='templates/message/list.pt',
             permission='imgw-message')
def view_list(request):
    p = dict()
    if request.POST:
        if 'lihat' in request.POST:
            p = get_filter(request)
        p['lihat'] = True
        return route_list(request, p)
    if 'awal' not in request.GET:
        p['awal'] = p['akhir'] = date.today()
        return route_list(request, p)    
    p = get_filter(request)        
    if 'kirim' in p:
        k = [p['kirim'] and '1' or '0']
        if 'status' in p:
            k.append(str(p['status']))
        kirim = ' '.join(k)
    else:
        kirim = None    
    r = dict(jenis_pesan=JENIS_PESAN,
             arus_pesan=ARUS_PESAN,
             kirim=kirim)
    if 'lihat' in request.GET:
        rows = get_rows(p)
        count = rows.count()
        rows = rows.order_by('id DESC')
        page_url = webhelpers.paginate.PageURL_WebOb(request)
        rows = webhelpers.paginate.Page(rows,
                    page=int(request.params.get('page', 1)),
                    item_count=count,
                    items_per_page=10,
                    url=page_url)
        r['rows'] = rows
        r['count'] = count
    return r
    
########
# Send #
########
def form_validator(form, value):
    t = value['pengirim'].split()
    jalur_id = int(t[0])
    if jalur_id != 1:
        return
    if 'penerima' not in value:
        if not t[1:]: # USSD tapi tidak ada pengirim ?
            raise colander.Invalid(form, 'Pesan USSD harus ada pengirimnya.')
        return
    msisdn = value['penerima']
    if msisdn[0] in ['0', '+']:
        msisdn = get_msisdn(msisdn)
        if not msisdn:
            raise colander.Invalid(form, 'Nomor penerima tidak benar.')
    try:
        int(msisdn)
    except ValueError:
        raise colander.Invalid(form, 'Nomor penerima tidak benar')
            

@colander.deferred
def pengirim_widget(node, kw):
    values = kw.get('daftar_pengirim', kw)
    return widget.SelectWidget(values=values)


class MessageSchema(colander.Schema):
    pengirim = colander.SchemaNode(
                colander.String(),
                widget=pengirim_widget)
    penerima = colander.SchemaNode(
                colander.String(),
                missing=colander.drop,
                description='Bisa nomor HP atau YM ID, sesuai Pengirim. ' + \
                            'Kosongkan bila mengirim USSD.')
    pesan = colander.SchemaNode(
                colander.String(),
                widget=widget.TextAreaWidget(rows=5, cols=60))


def save(values, request):
    p = dict(pesan=values['pesan'],
             kirim=True)
    t = values['pengirim'].split()
    p['jalur'] = int(t[0])           
    if p['jalur'] == 1 and values['penerima'].find('0') == 0:
        p['penerima'] = get_msisdn(values['penerima'])
    elif values['penerima']:
        p['penerima'] = values['penerima']
    if t[1:]:
        p['pengirim'] = t[1]
    outbox = ImAntrian()
    outbox.from_dict(p)
    DBSession.add(outbox)
    DBSession.flush()
    request.session.flash('Pesan sudah masuk antrian.')

def daftar_pengirim():
    r = []
    q = Jalur.query().filter(Jalur.id.in_([1, 4, 5, 6]))
    for row in q.order_by('id'):
        r.append((row.id, row.nama))
    q = DBSession.query(Agent)
    for row in q.order_by('jalur', 'id'):
        if row.jalur == 1 and row.modem:
            id = row.modem.msisdn
        else:
            id = row.id
        key = '%d %s' % (row.jalur, id)            
        if row.status == 0:
            if row.jalur == 1:
                status = '%d%%' % row.modem.signal
            else:
                status = 'ON'
        else:
            status = 'OFF'
        value = '%s %s %s' % (row.jalur_ref.nama, id, status)
        r.append((key, value))
    return r
    
def get_form(request):
    schema = MessageSchema(validator=form_validator)
    schema = schema.bind(daftar_pengirim=daftar_pengirim())
    schema.request = request
    return Form(schema, buttons=('kirim', 'batal'))

SESS_ADD_FAILED = 'imgw message add failed'

@view_config(route_name='imgw-message-add',
             renderer='templates/message/add.pt',
             permission='imgw-message-add')
def view_add(request):
    form = get_form(request)
    if request.POST:
        if 'kirim' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_ADD_FAILED] = e.render()
                url = request.route_url('imgw-message-add')
                return HTTPFound(location=url)
            save(dict(controls), request)
        return route_list(request)
    elif SESS_ADD_FAILED in request.session:
        r = dict(form=request.session[SESS_ADD_FAILED])
        del request.session[SESS_ADD_FAILED]
        return r
    return dict(form=form.render())

##########
# Resend #
##########
def daftar_pengirim_ulang(jalur):
    r = [('','Auto')]
    q = DBSession.query(Agent).filter_by(jalur=jalur)
    for row in q.order_by('jalur', 'id'):
        key = '%d %s' % (row.jalur, row.id)
        if row.jalur == 1 and row.modem:
            id = row.modem.msisdn
        else:
            id = row.id
        if row.status == 0:
            if row.jalur == 1:
                status = '%d%%' % row.modem.signal
            else:
                status = 'ON'
        else:
            status = 'OFF'
        value = '%s %s %s' % (row.jalur_ref.nama, id, status)
        r.append((key, value))
    return r


class ResendSchema(colander.Schema):
    pengirim = colander.SchemaNode(
                colander.String(),
                widget=pengirim_widget)
    tgl = colander.SchemaNode(
            colander.String(),
            missing=colander.drop,
            widget=widget.TextInputWidget(readonly=True))                
    penerima = colander.SchemaNode(
                colander.String(),
                missing=colander.drop,
                widget=widget.TextInputWidget(readonly=True))
    pesan = colander.SchemaNode(
                colander.String(),
                missing=colander.drop,
                widget=widget.TextAreaWidget(readonly=True))                
                
def get_resend_form(row, request):
    schema = ResendSchema()
    schema = schema.bind(daftar_pengirim=daftar_pengirim_ulang(row.jalur))
    return Form(schema, buttons=('kirim', 'batal'))

def save_resend(row, request):
    outbox = ImAntrian()
    outbox.jalur = row.jalur
    outbox.penerima = row.penerima
    outbox.pesan = row.pesan
    outbox.kirim = row.kirim
    outbox.parser = row.parser
    if request.POST['pengirim']:
        outbox.pengirim = request.POST['pengirim']
    DBSession.add(outbox)
    row.status = 4
    DBSession.add(row)
    DBSession.flush()
    msg = 'Pesan untuk %s sudah masuk antrian.' % outbox.penerima
    request.session.flash(msg)
    
@view_config(route_name='imgw-message-resend',
             renderer='templates/message/resend.pt',
             permission='imgw-message-resend')
def view_resend(request):
    row = ImSelesai.get_by_id(request.matchdict['id'])
    if not row:
        msg = 'ID pesan %d tidak ada.' % request.matchdict['id']
        request.session.flash(msg, 'error')
        url = request.route_url('imgw-message-resend')
        return HTTPFound(location=url)
    if not row.kirim:
        msg = 'ID pesan %d bukan jenis pengiriman.' % request.matchdict['id']
        request.session.flash(msg, 'error')
        url = request.route_url('imgw-message-resend')
        return HTTPFound(location=url)        
    form = get_resend_form(row, request)
    if request.POST:
        if 'kirim' in request.POST:
            save_resend(row, request)
        return route_list(request)
    values = dict(penerima=row.penerima,
                  pesan=row.pesan,
                  tgl=row.tgl_tz().strftime('%d-%m-%Y %H:%M:%S'))
    if row.pengirim:
        values['pengirim'] = row.pengirim
    return dict(form=form.render(appstruct=values))

