from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,unquote
import json,threading,mimetypes
from workflow import *
LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
 def reply(self,status,data,typ='application/json',headers=None):
  blob=json.dumps(data).encode() if typ=='application/json' else data
  self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(blob)));self.send_header('Cache-Control','no-store')
  for key,value in (headers or {}).items():self.send_header(key,value)
  self.end_headers();self.wfile.write(blob)
 def do_GET(self):
  path=unquote(urlparse(self.path).path)
  if path=='/api/manifest':return self.reply(200,load())
  if path=='/api/homepage-export.zip':
   try:
    with LOCK:blob=build_homepage_export(load())
    return self.reply(200,blob,'application/zip',{'Content-Disposition':'attachment; filename="redcatch-homepage-gallery.zip"'})
   except ValueError as e:return self.reply(400,{'error':str(e)})
   except Exception as e:return self.reply(500,{'error':str(e)})
  if path=='/':return self.reply(200,(ROOT/'organiser/index.html').read_bytes(),'text/html; charset=utf-8')
  if path.startswith('/media/'):
   q=(OUT/path[7:]).resolve()
   if q.is_relative_to(OUT.resolve()) and q.is_file() and q.suffix.lower() in EXT:return self.reply(200,q.read_bytes(),mimetypes.guess_type(q)[0] or 'application/octet-stream')
  if path.startswith('/original/'):
   a=load()['assets'].get(path[10:])
   if a:return self.reply(200,(ROOT/a['original_path']).read_bytes(),'image/jpeg')
  self.reply(404,{'error':'Not found'})
 def do_POST(self):
  if self.path!='/api/edit':return self.reply(404,{'error':'Not found'})
  if self.headers.get('Origin') and self.headers['Origin'] not in ['http://127.0.0.1:8765','http://localhost:8765']:return self.reply(403,{'error':'Local origin required'})
  try:
   if int(self.headers.get('Content-Length',0))>100000:raise ValueError('Request too large')
   data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   with LOCK:
    m=load();op=data['op'];pid=data.get('project');a=m['assets'].get(data.get('asset'));p=m['projects'].get(pid)
    metadata_only=op in ['hero','delete-empty-project','rename-project','homepage'] or (op=='project' and p is not None and data.get('category')==p['primary_category'])
    affected={pid, a.get('project_id') if a else None, data.get('destination')}
    if op=='create':
     pid=new_project(m,title=data.get('title') or 'New project');p=m['projects'][pid]
    elif op=='delete-empty-project':
     if not p:raise ValueError('Unknown project')
     if any(v['project_id']==pid for v in m['assets'].values()):raise ValueError('Only an empty project can be removed')
     del m['projects'][pid]
     m.setdefault('removed_project_ids',[]).append(pid)
    elif op=='homepage':
     if not a:raise ValueError('Unknown photograph')
     selected=data.get('selected')
     if not isinstance(selected,bool):raise ValueError('Selection must be true or false')
     if selected and not homepage_eligible(a):raise ValueError('Restore this photo before selecting it for the homepage')
     a['homepage_selected']=selected
    elif op=='rename-project':
     if not p:raise ValueError('Unknown project')
     title=data.get('title')
     if not isinstance(title,str) or not title.strip():raise ValueError('Enter a group name')
     if len(title.strip())>200:raise ValueError('Group name must be 200 characters or fewer')
     p['title']=title.strip()
    elif op=='approve-proposed-crops':
     proposals=[v for v in m['assets'].values() if v.get('crop',{}).get('decision')=='pending' and v['crop'].get('applied') and not v.get('error')]
     for v in proposals:
      x,y,r,b=v['crop']['box'];w,h=v['original_dimensions']
      if not (0<=x<r<=w and 0<=y<b<=h):raise ValueError('Invalid crop proposal: '+v['id'])
     for v in proposals:
      v['crop']['decision']='approved'
      affected.add(v['project_id'])
    elif op=='project':
     if data['category'] not in CATEGORIES:raise ValueError('Invalid category')
     status=data['status']
     if status not in ['pending','approved','ready']:raise ValueError('Invalid status')
     if status in ['approved','ready'] and not p['asset_ids']:raise ValueError('Cannot approve an empty project')
     if status=='ready' and any(v.get('crop',{}).get('decision')=='pending' for v in m['assets'].values() if v['project_id']==pid and v.get('portfolio_eligible')):raise ValueError('Review pending crops before marking this project ready')
     p.update(primary_category=data['category'],category_name=CATEGORIES[data['category']],review_status=status,title=data['title'],secondary_categories=[s.strip() for s in data['tags'].split(',') if s.strip()],description=data['description'])
    elif op=='move':
     dest=data.get('destination') or None
     if dest and dest not in m['projects']:raise ValueError('Unknown destination')
     a['project_id']=dest
    elif op=='merge':
     dest=data['destination']
     if dest==pid or dest not in m['projects']:raise ValueError('Choose a different project')
     for v in m['assets'].values():
      if v['project_id']==pid:v['project_id']=dest
     del m['projects'][pid];m['projects'][dest]['review_status']='pending'
    elif op=='split':
     selected=data['assets']
     if not selected or any(m['assets'][i]['project_id']!=pid for i in selected):raise ValueError('Select images from this project')
     dest=new_project(m)
     for i in selected:m['assets'][i]['project_id']=dest
    elif op=='hero':
     if a['project_id']!=pid or not a['portfolio_eligible']:raise ValueError('Choose an eligible photograph in this project')
     p['hero']=a['id']
    elif op=='crop':
     if data['decision'] not in ['approved','rejected','pending']:raise ValueError('Invalid crop decision')
     if 'box' in data:
      box=[int(v) for v in data['box']];w,h=a['original_dimensions']
      if len(box)!=4 or not (0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h):raise ValueError('Crop must lie inside the oriented original')
      a['crop'].update(box=box,applied=box!=[0,0,w,h],confidence='manual',evidence=['User specified crop coordinates'])
     a['crop']['decision']=data['decision']
    elif op=='image':
     if data['status'] not in ['pending','approved','unsuitable']:raise ValueError('Invalid image status')
     a['review_status']=data['status']
    elif op=='duplicate':
     decision=data['decision']
     if decision not in ['distinct','duplicate','pending']:raise ValueError('Invalid duplicate decision')
     preferred=data.get('preferred')
     if decision=='duplicate':
      if preferred==a['id'] or preferred not in m['assets']:raise ValueError('Choose a preferred version')
      other=m['assets'][preferred]
      if other['duplicate_status']=='exact' or other.get('duplicate_decision')=='duplicate':raise ValueError('Preferred image must itself be retained')
      a['preferred_version']=preferred
     a['duplicate_decision']=decision
    else:raise ValueError('Unknown operation')
    # Membership changes invalidate grouping; image edits preserve grouping approval.
    for key in affected:
     if key in m['projects']:
      if op in ['move','merge','split']:m['projects'][key]['review_status']='pending'
      elif op in ['crop','image','duplicate','hero','approve-proposed-crops'] and m['projects'][key]['review_status']=='ready':m['projects'][key]['review_status']='approved'
    backup=OUT/'manifests/previous-manifest.json';shutil.copy2(MAN,backup)
    if metadata_only:
     for v in m['assets'].values():
      if p and pid in m['projects'] and v['project_id']==pid and not v.get('error'):v['web_approved']=p['review_status'] in ['approved','ready'] and v['crop']['decision']!='pending'
     save(m)
    else:render(m)
    qa(m)
   self.reply(200,{'ok':True,'project':pid,**({'updated_crops':len(proposals)} if op=='approve-proposed-crops' else {})})
  except (ValueError,KeyError,TypeError) as e:self.reply(400,{'error':str(e)})
  except Exception as e:self.reply(500,{'error':str(e)})
if __name__=='__main__':
 print('Review at http://127.0.0.1:8765',flush=True);ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
