from email.utils import parseaddr
from sqlalchemy import not_
from pyramid.view import (
    view_config,
    )
from pyramid.httpexceptions import (
    HTTPFound,
    )
import colander
from deform import (
    Form,
    widget,
    ValidationFailure,
    )
from ...models import (
    DBSession,
    )
from ...models.parser import (
    SmsParsed,
    SmsWinner
    )
from ...tools import dict_to_str
from ...views.tools import _DTstrftime, _number_format
    
from datatables import ColumnDT, DataTables
from datetime import date, datetime, timedelta
from random import randrange
SESS_ADD_FAILED = 'parse-rnd add failed'
SESS_EDIT_FAILED = 'parse-rnd edit failed'

########                    
# List #
########    
@view_config(route_name='parse-rnd', renderer='parse-rnd/list.pt',
             permission='parse-rnd')
def view_list(request):
    return dict(project='OpenSIPKD IM')
    
##########                    
# Action #
##########    
@view_config(route_name='parse-rnd-act', renderer='json',
             permission='parse-rnd-act')
def view_act(request):
    ses = request.session
    req = request
    params = req.params
    url_dict = req.matchdict
    
    if url_dict['act']=='grid':
        columns = []
        columns.append(ColumnDT('id'))
        columns.append(ColumnDT('field01', filter = _DTstrftime, search_like='%s%%')) #tgl
        columns.append(ColumnDT('field02')) #notes1
        columns.append(ColumnDT('field03')) #notes2
        columns.append(ColumnDT('smsparsed.field01', filter = _DTstrftime)) #sender
        columns.append(ColumnDT('smsparsed.field02')) #cmd
        columns.append(ColumnDT('smsparsed.field03'))
        columns.append(ColumnDT('smsparsed.field04'))
        columns.append(ColumnDT('smsparsed.field05'))
        columns.append(ColumnDT('smsparsed.field06'))
        columns.append(ColumnDT('smsparsed.field07'))
        columns.append(ColumnDT('field04')) #flag
        query = DBSession.query(SmsWinner)
        rowTable = DataTables(req, SmsWinner, query, columns)
        return rowTable.output_result()    
    return
    
#######    
# Add #
#######
def email_validator(node, value):
    name, email = parseaddr(value)
    if not email or email.find('@') < 0:
        raise colander.Invalid(node, 'Invalid email format')

def form_validator(form, value):
    def err_email():
        raise colander.Invalid(form,
            'Email %s already used by parse-rnd ID %d' % (
                value['email'], found.id))

    def err_name():
        raise colander.Invalid(form,
            'User name %s already used by ID %d' % (
                value['parse-rnd_name'], found.id))
                
    if 'id' in form.request.matchdict:
        uid = form.request.matchdict['id']
        q = DBSession.query(User).filter_by(id=uid)
        row = q.first()
    else:
        row = None
    q = DBSession.query(User).filter_by(email=value['email'])
    found = q.first()
    if row:
        if found and found.id != parse-rnd.id:
            err_email()
    elif found:
        err_email()
    if 'parse-rnd_name' in value: # optional
        found = User.get_by_name(value['parse-rnd_name'])
        if parse-rnd:
            if found and found.id != parse-rnd.id:
                err_name()
        elif found:
            err_name()

@colander.deferred
def deferred_status(node, kw):
    values = kw.get('daftar_status', [])
    return widget.SelectWidget(values=values)
    
STATUS = (
    (1, 'Active'),
    (0, 'Inactive'),
    )    
    
class Int(colander.Int):
    def deserialize(self, value):
        if value is not None:
            return super(IntegerNone, self).deserialize(value)

    def serialize(self, node, appstruct):
        result = super(Int, self).serialize(node, appstruct)
        if result is not colander.null:
            result = int(result)
        else:
            result = 1
        return result

class ParSchema(colander.Schema):
    cmd = colander.SchemaNode(
                    colander.String(),
                    title = "Command",)
    date_from = colander.SchemaNode(
                    colander.Date(),
                    missing=colander.drop,
                    title="Date From")
                    
    date_to   = colander.SchemaNode(
                    colander.Date(),
                    missing=colander.drop,
                    title = "Date to",)
    is_winner   = colander.SchemaNode(
                    colander.Boolean(),
                    default = False,
                    title = "Include Winner",)                

def random_id(request):

    controls = dict(request.POST.items())
    if controls['date_to']:
        controls['date_to'] = (datetime.strptime(controls['date_to'],'%Y-%m-%d')+
                                        +timedelta(days=1)).strftime('%Y-%m-%d')
        
    qry = DBSession.query(SmsParsed)\
                 .filter(SmsParsed.field03==controls['cmd'].upper())

                 
    if 'is_winner' in controls and controls['is_winner']:
        qry = qry.filter(SmsParsed.field11<2)
    else:
        qry = qry.filter(SmsParsed.field11==0)
        
    if controls['date_from'] and controls['date_to']:
        qry = qry.filter(SmsParsed.field01 >= controls['date_from'], 
                         SmsParsed.field01 < controls['date_to'])
    
    count = qry.count()

    acak = 0
    if count:
      acak = randrange(1, count+1)
      
    return qry.order_by(SmsParsed.id).limit(acak)  
    #return DBSession.query(SmsWinner).filter_by(id=request.matchdict['id'])
    
@view_config(route_name='parse-rnd-par', renderer='parse-rnd/par.pt',
             permission='parse-rnd-par')
def view_par(request):
    form = get_form(request, ParSchema)
    if request.POST:
        if 'proses' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_ADD_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('parse-rnd-par'))
                #return dict(form=form)
            #save_param(dict(controls), request)
            rows = random_id(request).all()
            for row in rows:
                id = row.id
            if rows and row:
                controls2=dict(controls)
                url = request.route_url('parse-rnd-add', 
                                         _query={'id' :id, 
                                                 'cmd': controls2['cmd'],
                                                 'date_from': controls2['date_from'],
                                                 'date_to': controls2['date_to']})
                return HTTPFound(location=url)
            else:
                request.session[SESS_ADD_FAILED] = form.render()  
                request.session.flash('Tidak ditemukan Data Calon Pemenang','error')
                return HTTPFound(location=request.route_url('parse-rnd-par'))
                
        return route_list(request)
        
    elif SESS_ADD_FAILED in request.session:
        return session_failed(request, SESS_ADD_FAILED)
    return dict(form=form.render())
    #return dict(form=form)
    
class AddSchema(colander.Schema):
    cmd = colander.SchemaNode(
                    colander.String(),
                    missing=colander.drop,
                    widget=widget.HiddenWidget(readonly=True),
                    title = "Command",)
    date_from = colander.SchemaNode(
                    colander.Date(),
                    missing=colander.drop,
                    #widget=widget.HiddenWidget(readonly=True),
                    title="Date From")
                    
    date_to   = colander.SchemaNode(
                    colander.Date(),
                    missing=colander.drop,
                    #widget=widget.HiddenWidget(readonly=True),
                    title = "Date to",)
                    
    field01 = colander.SchemaNode(
                    colander.Date(),
                    missing=colander.drop,
                    #default=datetime.now(),
                    title = "Message Date",)
                    
    field02 = colander.SchemaNode(
                    colander.String(),
                    missing=colander.drop,
                    title = "Sender",)
                    
    field03 = colander.SchemaNode(
                    colander.String(),
                    missing=colander.drop,
                    title = "Cmd",)
                    
    field04 = colander.SchemaNode(
                    colander.String(),
                    missing=colander.drop,
                    title = "Field 04",)
                    
    field05 = colander.SchemaNode(
                    colander.String(),
                    missing=colander.drop,
                    title = "Field 05",)
                    
    field06 = colander.SchemaNode(
                    colander.String(),
                    missing=colander.drop,
                    title = "Field 06",)
                    
    field07 = colander.SchemaNode(
                    colander.String(),
                    missing=colander.drop,
                    title = "Field 07",)
                    
                    
    field01a = colander.SchemaNode(
                    colander.Date(),
                    default=datetime.now(),
                    title = "Process Date",)
    field02a = colander.SchemaNode(
                    colander.String(),
                    widget=widget.RichTextWidget(),
                    title = "Notes 1",)
    field03a = colander.SchemaNode(
                    colander.String(),
                    widget=widget.RichTextWidget(),
                    missing=colander.drop,
                    title = "Notes 2",)
                    
class EditSchema(AddSchema):
    #id disini adalah id sms message
    #id disini adalah id sms message
    id = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            #widget=widget.HiddenWidget(readonly=True)
            )
            
def get_form(request, class_form):
    schema = class_form() #validator=form_validator
    schema = schema.bind(daftar_status=STATUS)
    schema.request = request
    return Form(schema, buttons=('proses','cancel'))
    
def save(values, user, row=None):
    if not row:
        row = SmsWinner()
        #update sms parser karena satu orang hanya boleh satu pemenang

        q = DBSession.query(SmsParsed)
        q = q.filter(SmsParsed.field02== values['field02'], 
                          SmsParsed.field03==values['field03'])
        if values['date_to'] and values['date_from']:
            values['date_to'] = (datetime.strptime(values['date_to'],'%Y-%m-%d')+
                                 +timedelta(days=1)).strftime('%Y-%m-%d')
        #TODO: Kenapa gak bisa update kalau tanggal pram diisi                                
        #if values['date_from'] and values['date_to'] and True:
        #    q = q.filter(SmsParsed.field01 >= values['date_from'], 
        #              SmsParsed.field01 < values['date_to'])
        #print q
        q.update({"field11": 1})     
    values_to_save = {"smsparsed_id" : values['id'],
                      "field01" : values['field01a'],
                      "field02" : values['field02a'],
                      "field03" : values['field03a'],
                      }
                      
    row.from_dict(values_to_save)
    DBSession.add(row)
    DBSession.flush()
    return row
    
def save_request(values, request, row=None):
    if 'id' in request.matchdict:
        values['id'] = request.matchdict['id']
    row = save(values, request.user, row)
    request.session.flash('Winner %s berhasil disimpan.' % values['field02'])
        
def route_list(request):
    return HTTPFound(location=request.route_url('parse-rnd'))
    
def session_failed(request, session_name):
    r = dict(form=request.session[session_name])
    del request.session[session_name]
    return r
    
@view_config(route_name='parse-rnd-add', renderer='parse-rnd/add.pt',
             permission='parse-rnd-add')
def view_add(request):
    
    form = get_form(request, EditSchema)
    if request.POST:
        if 'proses' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_ADD_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('parse-rnd-add'))
                #return dict(form=form)
            save_request(dict(controls), request)
        return route_list(request)
    elif SESS_ADD_FAILED in request.session:
        return session_failed(request, SESS_ADD_FAILED)

    if request.POST and request.POST.items():
        controls = dict(request.POST.items())
    else:
        controls = dict(request.GET.items())
        
    row = DBSession.query(SmsParsed).filter_by(id=controls['id']).first()
    if not row:
        return id_not_found(request)
    values = row.to_dict()
    values.update(controls)
    values['date_from'] = values['date_from'] and datetime.strptime(values['date_from'],'%Y-%m-%d') or None
    values['date_to'] = values['date_to'] and datetime.strptime(values['date_to'],'%Y-%m-%d') or None
    
    return dict(form=form.render(appstruct=values))
    #return dict(form=form.render())
    #return dict(form=form)

########
# Edit #
########
def query_id(request):
    return DBSession.query(SmsWinner).filter_by(id=request.matchdict['id'])
    
def id_not_found(request):    
    msg = 'SMS ID %s not found.' % request.matchdict['id']
    request.session.flash(msg, 'error')
    return route_list(request)

@view_config(route_name='parse-rnd-edit', renderer='parse-rnd/edit.pt',
             permission='parse-rnd-edit')
def view_edit(request):
    row = query_id(request).first()
    if not row:
        return id_not_found(request)
    form = get_form(request, EditSchema)
    if request.POST:
        if 'proses' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_EDIT_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('parse-rnd-edit',
                                  id=row.id))
            save_request(dict(controls), request, row)
        return route_list(request)
    elif SESS_EDIT_FAILED in request.session:
        return session_failed(request, SESS_EDIT_FAILED)
    values = row.smsparsed.to_dict()
    values['field01a']=row.field01
    values['field02a']=row.field02
    values['field03a']=row.field03
    
    #values = dict_to_str(values)
    return dict(form=form.render(appstruct=values))
    #form.set_appstruct(values)
    #return dict(form=form)

##########
# Delete #
##########    
@view_config(route_name='parse-rnd-delete', renderer='parse-rnd/delete.pt',
             permission='parse-rnd-delete')
def view_delete(request):
    q = query_id(request)
    row = q.first()
    if not row:
        return id_not_found(request)
        
    form = Form(colander.Schema(), buttons=('delete','cancel'))
    if request.POST:
        if 'delete' in request.POST:
            msg = 'Message ID %d %s berhasil dihapus.' % (row.id, row.smsparsed.field02)
            q.delete()
            DBSession.flush()
            request.session.flash(msg)
        return route_list(request)
    return dict(row=row,
                 form=form.render())

##########
# Cencel #
##########    
@view_config(route_name='parse-rnd-cancel', renderer='parse-rnd/cancel.pt',
             permission='parse-rnd-cancel')
def view_cancel(request):
    q = query_id(request)
    row = q.first()
    if not row:
        return id_not_found(request)
        
    form = Form(colander.Schema(), buttons=('proses','cancel'))
    if request.POST:
        if 'proses' in request.POST:
            msg = 'Random Winner ID %d %s berhasil dibatalkan.' % (row.id, row.smsparsed.field02)
            row.field04 = 2 #delete()
            DBSession.add(row)
            DBSession.flush()
            request.session.flash(msg)
        return route_list(request)
    return dict(row=row,
                 form=form.render())

##########
# Delete #
##########    
@view_config(route_name='parse-rnd-approve', renderer='parse-rnd/approve.pt',
             permission='parse-rnd-approve')
def view_approve(request):
    q = query_id(request)
    row = q.first()
    if not row:
        return id_not_found(request)
        
    form = Form(colander.Schema(), buttons=('proses','cancel'))
    if request.POST:
        if 'proses' in request.POST:
            msg = 'Random Winner ID %d %s berhasil diapprove.' % (row.id, row.smsparsed.field02)
            row.field04 = 1 #delete()
            DBSession.add(row)
            DBSession.flush()
            request.session.flash(msg)
        return route_list(request)
    return dict(row=row,
                 form=form.render())

##########
# csv #
##########    
@view_config(route_name='parse-rnd-csv', renderer='csv',
             permission='parse-rnd-csv')
def export_csv(request):
    controls = dict(request.GET.items())
    
    q = DBSession.query(SmsWinner.field01.label('WinDate'), SmsWinner.field02.label('WinNotes1'), 
                        SmsWinner.field03.label('WinNotes2'), SmsWinner.field04.label('WinStatus'),  
                        SmsParsed.field00.label('RecvID'), SmsParsed.field01.label('RecvDate'), 
                        SmsParsed.field02.label('Sender'), SmsParsed.field03.label('RecvCmd'),
                        SmsParsed.field04, SmsParsed.field05, SmsParsed.field06, SmsParsed.field07).\
                  join(SmsParsed, SmsWinner.smsparsed_id==SmsParsed.id)
    if 'tgl' in controls and controls['tgl']:
        tgl2 = (datetime.strptime(controls['tgl'],'%Y-%m-%d')+timedelta(days=1)).strftime('%Y-%m-%d')
        q = q.filter(SmsWinner.field01>=controls['tgl'], SmsWinner.field01<tgl2)
    
    if 'cmd' in controls and controls['cmd']:
        q = q.filter(SmsParsed.field03==controls['cmd'])
        
        
    r = q.first()
    
    if r:
        header = r.keys()
        query = q.all()
        rows = []
        for item in query:
            rows.append(list(item))

        # override attributes of response
        filename = 'parsedmsg%s.csv' % datetime.now().strftime('%Y%m%d%H%M%S')

        request.response.content_disposition = 'attachment;filename=' + filename

        return {
              'header': header,
              'rows': rows,
            }
    return {
              'header': ['none'],
              'rows': ['none'],
            }                       