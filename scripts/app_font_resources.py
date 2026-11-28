"""Проверить SFNT-имена, лицензии и реальные glyph IDs без сторонних библиотек."""
import hashlib,struct

def inspect_font(data):
    def u16(offset):return struct.unpack_from('>H',data,offset)[0]
    tables={}
    for i in range(u16(4)):
        tag,_,offset,size=struct.unpack_from('>4sIII',data,12+i*16)
        assert offset+size<=len(data),'Обрезанная таблица TTF'
        tables[tag]=data[offset:offset+size]
    name=tables[b'name'];count,storage=struct.unpack_from('>HH',name,2);names={}
    for i in range(count):
        platform,encoding,language,key,length,offset=struct.unpack_from('>6H',name,6+i*12)
        raw=name[storage+offset:storage+offset+length]
        if platform in (0,3):
            text=raw.decode('utf-16-be')
            if key not in names or language==0x409:names[key]=text
    cmap=tables[b'cmap'];subtables=[]
    for i in range(struct.unpack_from('>H',cmap,2)[0]):
        platform,encoding,offset=struct.unpack_from('>HHI',cmap,4+8*i)
        if platform==0 or (platform==3 and encoding in (1,10)):
            format=struct.unpack_from('>H',cmap,offset)[0]
            if format in (4,12):subtables.append((format,cmap[offset:]))
    assert subtables,'Нет Unicode cmap'
    format,table=max(subtables,key=lambda x:x[0])
    def glyph(code):
        if format==12:
            for i in range(struct.unpack_from('>I',table,12)[0]):
                first,last,start=struct.unpack_from('>III',table,16+12*i)
                if first<=code<=last:return start+code-first
            return 0
        if code>0xffff:return 0
        count=struct.unpack_from('>H',table,6)[0]//2
        for i in range(count):
            end=struct.unpack_from('>H',table,14+2*i)[0];start=struct.unpack_from('>H',table,16+2*count+2*i)[0]
            if start<=code<=end:
                delta=struct.unpack_from('>h',table,16+4*count+2*i)[0]
                position=16+6*count+2*i;offset=struct.unpack_from('>H',table,position)[0]
                if not offset:return (code+delta)&0xffff
                value=struct.unpack_from('>H',table,position+offset+2*(code-start))[0]
                return (value+delta)&0xffff if value else 0
        return 0
    return names,glyph

def validate_fonts(source,registry):
    root=source/'submodules/Display/Resources/NagramiXFonts';checks=0
    sample='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'+''.join(chr(c) for c in range(0x410,0x450))+'Ёё'
    for record in registry['fonts']:
        data=(root/record['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==record['sha256']
        names,glyph=inspect_font(data)
        assert names[6]==record['postscript'] and names[0]==record['copyright'] and names[14]==record['license_url']
        assert ('Apache' in names.get(13,'') or 'apache.org' in names[14]) if record['file'].startswith('Roboto') else ('Open Font License' in names[13] and 'OFL' in names[14])
        for character in sample:
            assert glyph(ord(character))>0,(record['file'],character)
            checks+=1
    return {'faces':len(registry['fonts']),'glyph_checks':checks,'names_licenses_and_copyright':'passed','library':'Python standard library; independent SFNT name/cmap parser'}
