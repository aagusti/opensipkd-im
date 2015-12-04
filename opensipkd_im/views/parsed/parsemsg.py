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
    SmsParsed
    )
from ...tools import dict_to_str
    
from datatables import ColumnDT, DataTables


SESS_ADD_FAILED = 'parse-msg add failed'
SESS_EDIT_FAILED = 'parse-msg edit failed'

########                    
# List #
########    
@view_config(route_name='parse-msg', renderer='parse-msg/list.pt',
             permission='parse-msg')
def view_list(request):
    return dict(project='OpenSIPKD IM')
    
##########                    
# Action #
##########    
@view_config(route_name='parse-msg-act', renderer='json',
             permission='parse-msg-act')
def view_act(request):
    ses = request.session
    req = request
    params = req.params
    url_dict = req.matchdict
    
    if url_dict['act']=='grid':
        columns = []
        columns.append(ColumnDT('id'))
        columns.append(ColumnDT('field01')) #tgl
        columns.append(ColumnDT('field02')) #cmd
        columns.append(ColumnDT('field03')) #nama
        columns.append(ColumnDT('field04'))
        columns.append(ColumnDT('field05'))
        columns.append(ColumnDT('field06'))
        columns.append(ColumnDT('field07'))
        columns.append(ColumnDT('field08'))
        columns.append(ColumnDT('field09'))
        columns.append(ColumnDT('field11'))
        
        query = DBSession.query(SmsParsed)
        rowTable = DataTables(req, SmsParsed, query, columns)
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
            'Email %s already used by parse-msg ID %d' % (
                value['email'], found.id))

    def err_name():
        raise colander.Invalid(form,
            'User name %s already used by ID %d' % (
                value['parse-msg_name'], found.id))
                
    if 'id' in form.request.matchdict:
        uid = form.request.matchdict['id']
        q = DBSession.query(User).filter_by(id=uid)
        row = q.first()
    else:
        row = None
    q = DBSession.query(User).filter_by(email=value['email'])
    found = q.first()
    if row:
        if found and found.id != parse-msg.id:
            err_email()
    elif found:
        err_email()
    if 'parse-msg_name' in value: # optional
        found = User.get_by_name(value['parse-msg_name'])
        if parse-msg:
            if found and found.id != parse-msg.id:
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
        print 'deser---------------->', value
        if value is not None:
            return super(IntegerNone, self).deserialize(value)

    def serialize(self, node, appstruct):
        print '0-------------------------->'
        result = super(Int, self).serialize(node, appstruct)
        print '1-------------------------->', result
        if result is not colander.null:
            result = int(result)
        else:
            result = 1
        return result
        
class AddSchema(colander.Schema):
    field01 = colander.SchemaNode(
                    colander.String(),
                    title = "Command",)
    field02 = colander.SchemaNode(
                    colander.String(),
                    title = "Success",)
                    
    field03 = colander.SchemaNode(
                    colander.String(),
                    title = "Wrong Message",)
    field04 = colander.SchemaNode(
                    colander.String(),
                    title = "Allowed Receiver",)
    field05 = colander.SchemaNode(
                    colander.String(),
                    title = "Unique field",)
    field06 = colander.SchemaNode(
                    colander.String(),
                    title = "Unique Message",)
    field07 = colander.SchemaNode(
                    Int(),
                    missing = colander.null,
                    title = "Number of Content",)
                    
    field08 = colander.SchemaNode(
                    Int(),
                    widget=deferred_status, 
                    missing=None,
                    title = "Active",)
                    
class EditSchema(AddSchema):
    id = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            widget=widget.HiddenWidget(readonly=True))

def get_form(request, class_form):
    schema = class_form() #validator=form_validator
    schema = schema.bind(daftar_status=STATUS)
    schema.request = request
    return Form(schema, buttons=('save','cancel'))
    
def save(values, user, row=None):
    if not row:
        row = SmsParsed()
    row.from_dict(values)
    DBSession.add(row)
    DBSession.flush()
    return row
    
def save_request(values, request, row=None):
    if 'id' in request.matchdict:
        values['id'] = request.matchdict['id']
    row = save(values, request.user, row)
    request.session.flash('Konfig %s berhasil disimpan.' % row.field02)
        
def route_list(request):
    return HTTPFound(location=request.route_url('parse-msg'))
    
def session_failed(request, session_name):
    r = dict(form=request.session[session_name])
    del request.session[session_name]
    return r
    
@view_config(route_name='parse-msg-add', renderer='parse-msg/add.pt',
             permission='parse-msg-add')
def view_add(request):
    form = get_form(request, AddSchema)
    if request.POST:
        if 'save' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_ADD_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('parse-msg-add'))
                #return dict(form=form)
            save_request(dict(controls), request)
        return route_list(request)
    elif SESS_ADD_FAILED in request.session:
        return session_failed(request, SESS_ADD_FAILED)
    return dict(form=form.render())
    #return dict(form=form)

########
# Edit #
########
def query_id(request):
    return DBSession.query(SmsParsed).filter_by(id=request.matchdict['id'])
    
def id_not_found(request):    
    msg = 'User ID %s not found.' % request.matchdict['id']
    request.session.flash(msg, 'error')
    return route_list(request)

@view_config(route_name='parse-msg-edit', renderer='parse-msg/edit.pt',
             permission='parse-msg-edit')
def view_edit(request):
    row = query_id(request).first()
    if not row:
        return id_not_found(request)
    form = get_form(request, EditSchema)
    if request.POST:
        if 'save' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_EDIT_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('parse-msg-edit',
                                  id=row.id))
            save_request(dict(controls), request, row)
        return route_list(request)
    elif SESS_EDIT_FAILED in request.session:
        return session_failed(request, SESS_EDIT_FAILED)
    values = row.to_dict()
    #values = dict_to_str(values)
    return dict(form=form.render(appstruct=values))
    #form.set_appstruct(values)
    #return dict(form=form)

##########
# Delete #
##########    
@view_config(route_name='parse-msg-delete', renderer='parse-msg/delete.pt',
             permission='parse-msg-delete')
def view_delete(request):
    q = query_id(request)
    row = q.first()
    if not row:
        return id_not_found(request)
        
    form = Form(colander.Schema(), buttons=('delete','cancel'))
    if request.POST:
        if 'delete' in request.POST:
            msg = 'Message ID %d %s berhasil dihapus.' % (row.id, row.cmd)
            q.delete()
            DBSession.flush()
            request.session.flash(msg)
        return route_list(request)
    return dict(row=row,
                 form=form.render())

