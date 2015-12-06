from datetime import (
    date,
    datetime,
    timedelta,
    )
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from deform.interfaces import FileUploadTempStore
import webhelpers.paginate    
import colander
from deform import (
    Form,
    widget,
    FileData,    
    )
from ...models import (
    DBSession,
    User,
    )
from ...models.imgw import (
    Broadcast,
    BroadcastPenerima as BP,
    Status,
    ImSelesai,
    )
from ...tools import (
    create_date,
    create_now,
    get_settings,
    date_from_str,
    dict_to_str,
    create_datetime,
    )
from unggah import DbUpload


########
# List #
########
def route_list(request, p={}):
    q = dict_to_str(p)
    return HTTPFound(location=request.route_url('imgw-broadcast', _query=q))

def get_filter(request):
    p = dict(awal=date_from_str(request.params['awal']),
             akhir=date_from_str(request.params['akhir']))
    judul = request.params.get('judul')
    if judul:
        p['judul'] = judul
    return p
    
def get_rows(p):
    d = p['awal']
    awal = create_datetime(d.year, d.month, d.day)
    d = p['akhir'] + timedelta(1)
    akhir = create_datetime(d.year, d.month, d.day)
    rows = Broadcast.query().\
                     filter(Broadcast.tgl >= awal).\
                     filter(Broadcast.tgl < akhir)
    if 'judul' in p:
        pola = '%{judul}%'.format(judul=p['judul'])
        rows = rows.filter(Broadcast.judul.ilike(pola))
    return rows
    
    
@view_config(route_name='imgw-broadcast',
             renderer='templates/broadcast/list.pt',
             permission='imgw-broadcast')
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
    r = dict()
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

@view_config(route_name='imgw-broadcast-penerima',
             renderer='templates/broadcast/penerima.pt',
             permission='imgw-broadcast-penerima')
def view_list_penerima(request):
    bcast_id = request.matchdict['id']
    q = DBSession.query(Broadcast).filter_by(id=request.matchdict['id'])
    bcast = q.first()
    rows = DBSession.query(BP.id, BP.nama, BP.penerima, BP.pesan,
            Status.ket.label('ket_status'),
            ImSelesai.tgl_operator).filter(
            BP.status == Status.id).outerjoin(
            ImSelesai, BP.te == ImSelesai.id).filter(
            BP.id == request.matchdict['id'])
    count = rows.count()    
    rows = rows.order_by('urutan')
    page_url = webhelpers.paginate.PageURL_WebOb(request)
    rows = webhelpers.paginate.Page(rows,
                page=int(request.params.get('page', 1)),
                item_count=count,
                items_per_page=10,
                url=page_url)    
    return dict(
            bcast=bcast,
            rows=rows,
            count=count,
            )

##########
# Unggah #
##########
tmpstore = FileUploadTempStore()      
        
class AddSchema(colander.Schema):
    upload = colander.SchemaNode(
                FileData(),
                widget=widget.FileUploadWidget(tmpstore),
                title='Unggah')


def get_form(schema_cls):
    schema = schema_cls()
    return Form(schema, buttons=('simpan', 'batalkan'))        
        

@view_config(route_name='imgw-broadcast-file',
             renderer='templates/broadcast/file.pt',
             permission='imgw-broadcast-file')
def view_file(request):
    form = get_form(AddSchema)
    if request.POST:
        if 'simpan' in request.POST:
            dbu = DbUpload()
            dbu.save(request, 'upload', 'broadcast')
        return route_list(request)
    return dict(form=form.render())        
