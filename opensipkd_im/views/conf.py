from sqlalchemy import distinct
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
import colander
from deform import (
    Form,
    widget,
    ValidationFailure,
    )
from ..models import DBSession
from ..models.imgw import Conf
from ..tools import dict_to_str


########                    
# List #
########    
@view_config(route_name='conf', renderer='templates/conf/list.pt',
             permission='edit_conf')
def view_list(request):
    rows = DBSession.query(distinct(Conf.grup).label('grup')).order_by('grup')
    count = rows.count()
    return dict(rows=rows,
                 count=count)

@view_config(route_name='conf-grup', renderer='templates/conf/grup.pt',
             permission='edit_conf')
def view_grup_list(request):
    rows = DBSession.query(Conf).filter_by(grup=request.matchdict['grup']).\
            order_by('nama')
    return dict(rows=rows)    

#######    
# Add #
#######
SESS_ADD_FAILED = 'conf add failed'

class AddSchema(colander.Schema):
    grup = colander.SchemaNode(colander.String())
    nama = colander.SchemaNode(colander.String())
    nilai = colander.SchemaNode(colander.String(),
                widget=widget.TextAreaWidget(rows=5))
    ket = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            widget=widget.TextAreaWidget(rows=5),
            title='Keterangan')


def add_form_validator(form, value):
    def err_found():
        raise colander.Invalid(form,
            'Konfigurasi %s - %s sudah ada.' % (
                value['grup'], value['nama']))
                
    found = DBSession.query(Conf).filter_by(grup=value['grup'],
                nama=value['nama']).first()
    if found:
        err_found()
                    

def get_form(request, class_form, validator=None):
    schema = class_form(validator=validator)
    schema.request = request
    return Form(schema, buttons=('save','cancel'))
    
def save(values, user, row=None):
    if not row:
        row = Conf()
    row.from_dict(values)
    DBSession.add(row)
    DBSession.flush()
    return row
    
def save_request(values, request, row=None):
    if 'nama' in request.matchdict:
        values['grup'] = request.matchdict['grup']
        #values['nama'] = request.matchdict['nama']
    row = save(values, request.user, row)
    request.session.flash('Konfigurasi %s - %s sudah disimpan.' % (row.grup,
        row.nama))
        
def route_list(request):
    return HTTPFound(location=request.route_url('conf'))
    
def route_grup_list(request, grup):    
    return HTTPFound(location=request.route_url('conf-grup', grup=grup))
    
def session_failed(request, session_name):
    r = dict(form=request.session[session_name])
    del request.session[session_name]
    return r
    
@view_config(route_name='conf-add', renderer='templates/conf/add.pt',
             permission='edit_conf')
def view_add(request):
    form = get_form(request, AddSchema, add_form_validator)
    if request.POST:
        if 'save' in request.POST:
            controls = request.POST.items()
            try:
                c = form.validate(controls)
            except ValidationFailure, e:
                request.session[SESS_ADD_FAILED] = e.render()               
                return HTTPFound(location=request.route_url('conf-add'))
            save_request(dict(controls), request)
        #return route_grup_list(request, request.POST.get('grup'))
        return route_list(request)
    elif SESS_ADD_FAILED in request.session:
        return session_failed(request, SESS_ADD_FAILED)
    values = dict()
    if 'grup' in request.GET:
        values['grup'] = request.GET['grup']
    return dict(form=form.render(appstruct=values))

########
# Edit #
########
SESS_EDIT_FAILED = 'conf edit failed'

def query_id(request):
    return DBSession.query(Conf).filter_by(grup=request.matchdict['grup'],
                nama=request.matchdict['nama'])
    
def id_not_found(request):    
    msg = 'Konfigurasi %s - %s tidak ada' % (request.matchdict['grup'],
            request.matchdict['nama'])
    request.session.flash(msg, 'error')
    return route_list(request)


class EditSchema(colander.Schema):
    grup = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            widget=widget.TextInputWidget(readonly=True))
    nama = colander.SchemaNode(colander.String())
    nilai = colander.SchemaNode(colander.String(),
                widget=widget.TextAreaWidget(rows=10, cols=60))
    ket = colander.SchemaNode(colander.String(),
            missing=colander.drop,
            widget=widget.TextAreaWidget(rows=10, cols=60),
            title='Keterangan')

@view_config(route_name='conf-edit', renderer='templates/conf/edit.pt',
             permission='edit_conf')
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
                return HTTPFound(location=request.route_url('conf-edit',
                                  grup=row.grup, nama=row.nama))
            save_request(dict(controls), request, row)
        return route_grup_list(request, row.grup)
    elif SESS_EDIT_FAILED in request.session:
        return session_failed(request, SESS_EDIT_FAILED)
    values = row.to_dict()
    values = dict_to_str(values)
    return dict(form=form.render(appstruct=values))

##########
# Delete #
##########    
@view_config(route_name='conf-delete', renderer='templates/conf/delete.pt',
             permission='edit_conf')
def view_delete(request):
    q = query_id(request)
    row = q.first()
    if not row:
        return id_not_found(request)
    form = Form(colander.Schema(), buttons=('delete','cancel'))
    if request.POST:
        if 'delete' in request.POST:
            msg = 'Konfigurasi %s - %s berhasil dihapus.' % (row.grup, row.nama)
            q.delete()
            DBSession.flush()
            request.session.flash(msg)
        return route_grup_list(request, row.grup)
    return dict(row=row,
                 form=form.render())

