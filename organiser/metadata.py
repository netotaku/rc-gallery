"""Small read-only JPEG EXIF reader; no filename dates treated as capture evidence."""
import struct

def exif_metadata(path):
 result={'capture_date':None,'exif_orientation':1,'capture_date_source':None}
 if path.suffix.lower() not in {'.jpg','.jpeg'}:return result
 try:
  data=path.read_bytes();pos=2
  while pos+4<len(data):
   if data[pos]!=255:break
   marker=data[pos+1];pos+=2
   if marker in [0xDA,0xD9]:break
   size=int.from_bytes(data[pos:pos+2],'big');chunk=data[pos+2:pos+size];pos+=size
   if marker!=0xE1 or not chunk.startswith(b'Exif\0\0'):continue
   t=chunk[6:];endian='<' if t[:2]==b'II' else '>'
   def u16(o):return struct.unpack_from(endian+'H',t,o)[0]
   def u32(o):return struct.unpack_from(endian+'I',t,o)[0]
   def directory(offset):
    found={}
    for n in range(min(u16(offset),1000)):
     o=offset+2+n*12;tag=u16(o);typ=u16(o+2);count=u32(o+4);length=count*{1:1,2:1,3:2,4:4}.get(typ,0)
     if not length:continue
     start=o+8 if length<=4 else u32(o+8)
     raw=t[start:start+length]
     if typ==2:value=raw.rstrip(b'\0').decode('ascii','replace')
     elif typ==3:value=struct.unpack_from(endian+'H',raw)[0]
     elif typ==4:value=struct.unpack_from(endian+'I',raw)[0]
     else:continue
     found[tag]=value
    return found
   first=directory(u32(4));result['exif_orientation']=first.get(274,1)
   sub=directory(first[34665]) if 34665 in first else {}
   if sub.get(36867):result.update(capture_date=sub[36867],capture_date_source='EXIF DateTimeOriginal')
   break
 except (ValueError,IndexError,struct.error):pass
 return result
