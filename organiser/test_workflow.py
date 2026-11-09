import unittest,tempfile,hashlib,json,threading,urllib.request,urllib.error
from pathlib import Path
import cv2,numpy as np
import workflow as w
import server as s
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
  self.old=(w.ROOT,w.OUT,w.MAN)
  w.ROOT=root;w.OUT=root/'portfolio';w.MAN=w.OUT/'manifests/manifest.json'
  for k in ['ROOT','OUT','MAN']:setattr(s,k,getattr(w,k))
  rng=np.random.default_rng(42);self.photo=rng.integers(30,250,(80,120,3),dtype=np.uint8)
  cv2.imwrite(str(root/'a.jpg'),self.photo);(root/'b.jpg').write_bytes((root/'a.jpg').read_bytes())
  framed=np.pad(self.photo,((20,20),(0,0),(0,0)));cv2.imwrite(str(root/'c.png'),framed)
  self.hashes={p.name:w.digest(p) for p in root.iterdir()};self.m=w.scan()
 def tearDown(self):
  w.ROOT,w.OUT,w.MAN=self.old
  for k in ['ROOT','OUT','MAN']:setattr(s,k,getattr(w,k))
  self.tmp.cleanup()
 def test_preservation_idempotency_and_output_exclusion(self):
  pid=w.new_project(self.m,'domestic');a=next(iter(self.m['assets'].values()));a['project_id']=pid;self.m['projects'][pid]['review_status']='approved';w.render(self.m)
  before=w.MAN.read_text();again=w.scan()
  self.assertEqual(len(again['assets']),3);self.assertEqual(again['projects'][pid]['review_status'],'approved');self.assertEqual(w.MAN.read_text(),before)
  self.assertEqual(w.qa(again)['errors'],[])
  for name,sha in self.hashes.items():self.assertEqual(w.digest(w.ROOT/name),sha)
  self.assertEqual(sum(a['duplicate_status']=='exact' for a in again['assets'].values()),1)
  (w.ROOT/'d.jpg').write_bytes((w.ROOT/'a.jpg').read_bytes());third=w.scan()
  added=next(a for a in third['assets'].values() if a['original_filename']=='d.jpg')
  self.assertEqual(added['duplicate_status'],'exact');self.assertEqual(third['assets'][added['preferred_version']]['duplicate_status'],'unique')
 def test_crop_conservative_and_rejection(self):
  proposal=w.crop_proposal(np.pad(self.photo,((20,20),(0,0),(0,0))))
  self.assertEqual(proposal['box'],[0,20,120,100]);self.assertFalse(w.crop_proposal(np.zeros((80,120,3),np.uint8))['applied'])
  a=next(a for a in self.m['assets'].values() if a['original_filename']=='c.png');a['crop']['decision']='rejected';w.render(self.m)
  self.assertEqual(a['processed_dimensions'],[120,120])
 def test_http_edit_persistence_move_split_merge(self):
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  url=f'http://127.0.0.1:{http.server_port}'
  def edit(data):
   request=urllib.request.Request(url+'/api/edit',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
   return json.load(urllib.request.urlopen(request))
  try:
   pid=edit({'op':'create','title':'Test'})['project'];ids=list(self.m['assets']);aid=ids[0]
   edit({'op':'move','asset':aid,'destination':pid});edit({'op':'move','asset':ids[2],'destination':pid})
   self.assertEqual(w.load()['assets'][aid]['project_id'],pid)
   edit({'op':'split','project':pid,'assets':[aid]});m=w.load();other=m['assets'][aid]['project_id'];self.assertNotEqual(pid,other)
   edit({'op':'merge','project':other,'destination':pid});m=w.load();self.assertNotIn(other,m['projects']);self.assertEqual(m['assets'][aid]['project_id'],pid)
   self.assertEqual(w.qa(m)['errors'],[])
   with self.assertRaises(urllib.error.HTTPError):edit({'op':'delete-empty-project','project':pid})
   empty=edit({'op':'create','title':'Empty project'})['project']
   edit({'op':'delete-empty-project','project':empty})
   self.assertNotIn(empty,w.load()['projects']);self.assertIn(empty,w.load()['removed_project_ids'])
   edit({'op':'hero','project':pid,'asset':aid});self.assertEqual(w.load()['projects'][pid]['hero'],aid)
   cropid=ids[2]
   approval={'op':'project','project':pid,'category':'needs-review','status':'approved','title':'Test','tags':'','description':'Visible evidence'}
   edit(approval);self.assertEqual(w.load()['projects'][pid]['review_status'],'approved')
   with self.assertRaises(urllib.error.HTTPError):edit(dict(approval,status='ready'))
   self.assertEqual(w.load()['projects'][pid]['review_status'],'approved')
   bulk=edit({'op':'approve-proposed-crops'});self.assertEqual(bulk['updated_crops'],1)
   self.assertEqual(w.load()['assets'][cropid]['crop']['decision'],'approved')
   self.assertEqual(w.load()['projects'][pid]['review_status'],'approved')
   self.assertEqual(edit({'op':'approve-proposed-crops'})['updated_crops'],0)
   edit({'op':'rename-project','project':pid,'title':'  Updated group name  '})
   self.assertEqual(w.load()['projects'][pid]['title'],'Updated group name')
   self.assertEqual(w.load()['projects'][pid]['review_status'],'approved')
   with self.assertRaises(urllib.error.HTTPError):edit({'op':'rename-project','project':pid,'title':'   '})
   edit({'op':'crop','asset':cropid,'decision':'approved','box':[0,20,120,100]})
   self.assertEqual(w.load()['assets'][cropid]['processed_dimensions'],[120,80])
   self.assertEqual(w.load()['projects'][pid]['review_status'],'approved')
   edit({'op':'project','project':pid,'category':'domestic','status':'approved','title':'Verified test','tags':'Roof access scaffolding','description':'Test evidence'})
   self.assertEqual(w.load()['projects'][pid]['review_status'],'approved')
   edit({'op':'image','asset':cropid,'status':'unsuitable'})
   self.assertFalse(w.load()['assets'][cropid]['portfolio_eligible'])
   with self.assertRaises(urllib.error.HTTPError):edit({'op':'crop','asset':cropid,'decision':'approved','box':[-1,0,1000,1000]})
   import io,zipfile
   with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+'/api/homepage-export.zip')
   approvals={k:p['review_status'] for k,p in w.load()['projects'].items()}
   heroes={k:p['hero'] for k,p in w.load()['projects'].items()}
   edit({'op':'homepage','asset':aid,'selected':True})
   self.assertTrue(w.load()['assets'][aid]['homepage_selected'])
   with self.assertRaises(urllib.error.HTTPError):edit({'op':'homepage','asset':cropid,'selected':True})
   with self.assertRaises(urllib.error.HTTPError):edit({'op':'homepage','asset':aid,'selected':'true'})
   edit({'op':'image','asset':cropid,'status':'pending'})
   edit({'op':'homepage','asset':cropid,'selected':True})
   response=urllib.request.urlopen(url+'/api/homepage-export.zip')
   self.assertEqual(response.headers['Content-Type'],'application/zip')
   self.assertIn('attachment',response.headers['Content-Disposition'])
   with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
    self.assertEqual(len(archive.namelist()),2)
    self.assertTrue(all(name.endswith('.jpg') and '/' not in name for name in archive.namelist()))
    index=json.loads((w.OUT/'exports/homepage-gallery-index.json').read_text())
    entry=next(v for v in index['images'] if v['asset_id']==cropid)
    image=cv2.imdecode(np.frombuffer(archive.read(entry['export_filename']),dtype=np.uint8),cv2.IMREAD_COLOR)
    self.assertEqual(list(image.shape[1::-1]),[120,80])
   self.assertEqual({k:p['review_status'] for k,p in w.load()['projects'].items()},approvals)
   self.assertEqual({k:p['hero'] for k,p in w.load()['projects'].items()},heroes)
   edit({'op':'homepage','asset':aid,'selected':False})
   with zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url+'/api/homepage-export.zip').read())) as archive:self.assertEqual(len(archive.namelist()),1)
   self.assertEqual(len(list((w.OUT/'exports/homepage-gallery').glob('*.jpg'))),1)
   self.assertTrue(w.scan()['assets'][cropid]['homepage_selected'])
   for name,sha in self.hashes.items():self.assertEqual(w.digest(w.ROOT/name),sha)
   with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+'/media/../../organiser/config.json')
  finally:http.shutdown();http.server_close()
if __name__=='__main__':unittest.main()
