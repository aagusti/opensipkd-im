from urllib import quote_plus, unquote_plus, urlencode
from urlparse import urlparse
from datetime import date, datetime
from types import UnicodeType, StringType

DateType = type(date.today())
DateTimeType = type(datetime.now())

# Ada 3 jenis driver:
# 1. URL standar seperti PostgreSQL, MySQL, Oracle: DRIVER://USER:PASS@HOST:PORT/NAME
# 2. URL file seperti SQLite: DRIVER:///FILENAME
# 3. URL ODBC: DRIVER+pyodbc:///?odbc_connect=QUOTED_ODBC_CONF


def extract_netloc(s): # sugiana:a@localhost:5432
    r = {}
    t = s.split('@')
    if t[1:]: # localhost:5432
        h = t[1].split(':')
        if h[1:]:
            r['port'] = int(h[1])
        r['host'] = h[0]
    auth = t[0].split(':')
    if auth[1:]:
        r['pass'] = auth[1]
    r['user'] = auth[0]
    return r

def extract_db_url(db_url):
    p = urlparse(db_url)
    r = {'driver': p.scheme}
    if is_odbc(p.scheme):
        if p.query:
            s = p.query
        else:
            s = p.path.split('?')[-1]
        t = s.split('=')
        s = unquote_plus(t[1])    
        r.update(extract_tds(s))
        return r
    if p.netloc:
        r.update(extract_netloc(p.netloc))
    if p.path[1:]:
        r['name'] = p.path.lstrip('/')
    return r

def create_db_url(p):
    if not is_val('driver', p):
        return ''
    url = p['driver'] + '://'
    if p['driver'].split('+')[-1] == 'pyodbc':
        s = quote_plus(create_tds(p))
        return url + '/?odbc_connect={}'.format(s)
    if is_val('user', p):
        url += p['user']
        if is_val('pass', p):
            url += ':' + p['pass']
    if is_val('host', p):
        url += '@' + p['host']
        if is_val('port', p):
            url += ':' + str(p['port'])
    if is_val('name', p):
        url += '/' + p['name']
    return url
    
def create_tds(p):
    r = {'DRIVER': '{FreeTDS}',
         'TDS_Version': '7.0'}
    if is_val('user', p):
        r['UID'] = p['user']
        if is_val('pass', p):
            r['PWD'] = p['pass']
    if is_val('name', p):
        r['Database'] = p['name']
    if is_val('port', p):
        r['Port'] = str(p['port'])
    if is_val('host', p):
        r['Server'] = p['host']
    items = []
    for key in r:
        value = r[key]
        item = '='.join([key, value])
        items.append(item)
    return ';'.join(items)

def extract_tds(s):
    items = s.split(';')
    r = {}
    for item in items:
        key, value = item.split('=')
        if key == 'UID':
            r['user'] = value
        elif key == 'PWD':
            r['pass'] = value
        elif key == 'Server':
            r['host'] = value
        elif key == 'Database':
            r['name'] = value
        elif key == 'Port':
            r['port'] = int(value)
    return r
    
def is_odbc(driver):
    return driver.split('+')[-1] == 'pyodbc'
    
def is_val(key, p):
    return key in p and p[key]    
        
def date_from_str(s):
    y, m, d = s.split('-')
    if len(y) < 3: # dmy ?
        d, y = y, d
    y, m, d = map(lambda x: int(x), [y, m, d])
    return date(y, m, d)
    
def dmy(tgl):
    return tgl.strftime('%d-%m-%Y')
    
def dmyhms(t):
    return t.strftime('%d-%m-%Y %H:%M:%S')
    
def to_str(v):
    typ = type(v)
    if typ == DateType:
        return dmy(v)
    if typ == DateTimeType:
        return dmyhms(v)
    if v == 0:
        return '0'
    if typ in [UnicodeType, StringType]:
        return v.strip()
    return v and str(v) or ''
    
def dict_to_str(d):
    r = {}
    for key in d:
        val = d[key]
        r[key] = to_str(val)
    return r

def url_encode(p):
    p = dict_to_str(p)
    return urlencode(p)

def is_value(key, params):
    return key in params and params[key]
    
def clean(s):
    r = ''
    for ch in s:
        if ord(ch) > 126:
            ch = ' '
        r += ch
    return r
    

if __name__ == '__main__':
    import sys
    normal_example = 'postgresql://sugiana:a@localhost:5432/template1'
    file_example = 'sqlite:///filename'
    db_conf = 'DRIVER={FreeTDS};Server=192.168.1.2;Database=dbsms;UID=testing;PWD=1234;Port=1433;TDS_Version=7.0'
    quoted = quote_plus(db_conf)
    odbc_example = 'mssql+pyodbc:///?odbc_connect={}'.format(quoted)
    odbc_example = 'mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BFreeTDS%7D%3BServer%3D172.16.64.77%3BDatabase%3Ddbsms%3BUID%3Dtesting%3BPWD%3D1234%3BPort%3D1433%3BTDS_Version%3D7.0'
    examples = [normal_example, file_example, odbc_example]
    for db_url in examples:
        p = extract_db_url(db_url)
        db_url_recreate = create_db_url(p)
        ok = db_url == db_url_recreate
        print('%s -> %s -> %s match %s' % (db_url, p, db_url_recreate, ok))
