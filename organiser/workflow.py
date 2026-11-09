"""Non-destructive, content-addressed image inventory and review workflow."""
from pathlib import Path
import cv2, numpy as np, hashlib, json, shutil, os, argparse
from metadata import exif_metadata
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'portfolio'; MAN=OUT/'manifests/manifest.json'
CONFIG=json.loads((ROOT/'organiser/config.json').read_text())
EXT={'.jpg','.jpeg','.png','.webp','.heic','.heif'}
CATEGORIES={'domestic':'Domestic Scaffolding','commercial':'Commercial Scaffolding','temporary-roofs':'Temporary Roofs / False Roofs','needs-review':'Needs review'}
def save(m):
 MAN.parent.mkdir(parents=True,exist_ok=True)
 temp=MAN.with_suffix('.tmp'); temp.write_text(json.dumps(m,indent=2)); os.replace(temp,MAN)
def load(): return json.loads(MAN.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 im=cv2.imread(str(p)) # OpenCV applies EXIF orientation by default.
 if im is None and p.suffix.lower() in {'.heic','.heif'}:
  import subprocess,tempfile
  with tempfile.TemporaryDirectory() as d:
   q=Path(d)/'decoded.png'; subprocess.run(['sips','-s','format','png',str(p),'--out',str(q)],check=True,capture_output=True); im=cv2.imread(str(q))
 if im is None: raise ValueError('Image decoder could not read file')
 return im

def crop_proposal(im):
 h,w=im.shape[:2]; small=cv2.resize(im,(min(w,800),max(1,round(h*min(w,800)/w))))
 dark=np.max(small,axis=2)<CONFIG['black_threshold']; bounds=[0,0,small.shape[1],small.shape[0]]; evidence=[]
 for axis,reverse,index in [(0,False,1),(0,True,3),(1,False,0),(1,True,2)]:
  values=dark.mean(axis=1 if axis==0 else 0); seq=values[::-1] if reverse else values
  n=0
  for v in seq:
   if v<CONFIG['edge_fraction']: break
   n+=1
  # Require a substantial, uniform border and an abrupt transition.
  if n>=8 and n<len(seq)*.35 and seq[n:min(n+16,len(seq))].mean()<.95:
   bounds[index]=len(seq)-n if reverse else n; evidence.append('uniform near-black edge with abrupt transition')
 scale=w/small.shape[1]; box=[round(v*scale) for v in bounds]; box[2]=min(w,box[2]);box[3]=min(h,box[3])
 applied=box!=[0,0,w,h]
 return {'box':box,'confidence':'high' if len(evidence)>=2 else 'medium' if applied else 'none','evidence':evidence,'decision':'pending' if applied else 'none','applied':applied}

def dhash(im):
 gray=cv2.cvtColor(cv2.resize(im,(9,8)),cv2.COLOR_BGR2GRAY); return int(''.join('1' if v else '0' for v in (gray[:,1:]>gray[:,:-1]).flatten()),2)
def resize(im,limit):
 h,w=im.shape[:2]; ratio=min(1,limit/max(h,w));return cv2.resize(im,(max(1,round(w*ratio)),max(1,round(h*ratio)))) if ratio<1 else im

def new_project(m,category='needs-review',title='Unconfirmed scaffolding project',evidence='',confidence='low'):
 n=m['next_project'];m['next_project']+=1;pid=f'project-{n:03d}'
 m['projects'][pid]={'id':pid,'primary_category':category,'category_name':CATEGORIES[category],'secondary_categories':[],'grouping_confidence':confidence,'evidence':evidence,'review_status':'pending','title':title,'description':evidence,'hero':None,'content_assessment':{'potential_relevance':'Requires visual and client confirmation','demonstrates':evidence,'information_needed':['Confirm site identity and permission to publish','Confirm service scope, location if desired, dates and project context'],'repetitive_images':'Review duplicate candidates and alternate angles'}}
 return pid

def render(m):
 for name in [*CATEGORIES,'duplicates','thumbnails','manifests','reports']: (OUT/name).mkdir(parents=True,exist_ok=True)
 expected=set()
 for a in m['assets'].values():
  if a.get('error'):continue
  im=read(ROOT/a['original_path']); crop=a['crop']; x,y,r,b=crop['box']
  clean=im[y:b,x:r] if crop['applied'] and crop['decision']!='rejected' else im
  a['processed_dimensions']=[clean.shape[1],clean.shape[0]]
  p=m['projects'].get(a['project_id']);cat=p['primary_category'] if p else 'needs-review'
  base=Path('duplicates')/a['id'] if a['duplicate_status']=='exact' or a.get('duplicate_decision')=='duplicate' else Path(cat)/(a['project_id'] or 'unassigned')/a['id']
  # Stable image ID suffix prevents overwrite on move, merge or new ingestion.
  unchanged=clean.shape==im.shape and not a.get('exif_orientation',1)>1
  master=base.with_suffix(Path(a['original_path']).suffix.lower() if unchanged else '.png')
  web=Path(str(base)+'-web.webp');thumb=Path('thumbnails')/(a['id']+'.webp')
  for q in [master,web,thumb]: (OUT/q).parent.mkdir(parents=True,exist_ok=True); expected.add(str(q))
  if unchanged: shutil.copy2(ROOT/a['original_path'],OUT/master)
  else: cv2.imwrite(str(OUT/master),clean)
  cv2.imwrite(str(OUT/web),resize(clean,CONFIG['web_max']),[cv2.IMWRITE_WEBP_QUALITY,CONFIG['web_quality']])
  cv2.imwrite(str(OUT/thumb),resize(clean,CONFIG['thumbnail_max']),[cv2.IMWRITE_WEBP_QUALITY,80])
  a.update(cleaned_path=str(master),web_path=str(web),thumbnail_path=str(thumb),portfolio_eligible=a['review_status']!='unsuitable' and a['duplicate_status']!='exact' and a.get('duplicate_decision')!='duplicate',web_approved=bool(p and p['review_status'] in ['approved','ready'] and crop['decision']!='pending'))
  if a.get('homepage_selected') and not homepage_eligible(a):a['homepage_selected']=False
 # Remove only previously generated assets that were moved. Originals are outside OUT.
 for old in m.get('generated_paths',[]):
  if old not in expected:
   q=(OUT/old).resolve()
   if q.is_relative_to(OUT.resolve()) and q.is_file():q.unlink()
 m['generated_paths']=sorted(expected)
 for pid,p in m['projects'].items():
  members=[a for a in m['assets'].values() if a['project_id']==pid]; eligible=[a for a in members if a.get('portfolio_eligible')]
  p['asset_ids']=[a['id'] for a in members]
  if p['hero'] not in [a['id'] for a in eligible]:p['hero']=max(eligible,key=lambda a:np.prod(a['processed_dimensions']))['id'] if eligible else None
  p['original_filenames']=[a['original_filename'] for a in members]
 save(m)

def homepage_eligible(a):
 return not a.get('error') and a['review_status']!='unsuitable' and a['duplicate_status']!='exact' and a.get('duplicate_decision')!='duplicate'

def build_homepage_export(m):
 """Export only the user's selected, retained photographs; preserve project assignments."""
 import io,zipfile,re,unicodedata
 selected=[a for a in m['assets'].values() if a.get('homepage_selected') and homepage_eligible(a)]
 if not selected:raise ValueError('Select at least one photo for the homepage gallery first')
 if any(a['crop']['decision']=='pending' for a in selected):raise ValueError('Review pending crops on selected homepage photos before downloading')
 files=[];mapping=[]
 for n,a in enumerate(selected,1):
  p=m['projects'].get(a['project_id']);title=p['title'] if p else 'scaffolding'
  slug=re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode().lower()).strip('-')[:65] or 'scaffolding'
  name=f"{n:03d}-redcatch-{slug}-{a['id']}.jpg"
  master=(OUT/a['cleaned_path']).resolve()
  if not master.is_relative_to(OUT.resolve()):raise ValueError('Invalid clean master path')
  image=resize(read(master),CONFIG.get('homepage_max',2500))
  ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,CONFIG.get('homepage_jpeg_quality',90)])
  if not ok:raise ValueError('Could not export '+a['id'])
  blob=encoded.tobytes()
  if len(blob)>20_000_000:raise ValueError('Export exceeds the image upload size limit: '+a['id'])
  files.append((name,blob));mapping.append({'asset_id':a['id'],'project_id':a['project_id'],'source_filename':a['original_filename'],'export_filename':name,'dimensions':[image.shape[1],image.shape[0]],'bytes':len(blob)})
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
  for name,blob in files:archive.writestr(name,blob)
 exports=OUT/'exports';folder=exports/'homepage-gallery';folder.mkdir(parents=True,exist_ok=True)
 index=exports/'homepage-gallery-index.json'
 previous=json.loads(index.read_text()) if index.exists() else {'images':[]}
 names={name for name,blob in files}
 for name,blob in files:
  temp=folder/(name+'.tmp');temp.write_bytes(blob);os.replace(temp,folder/name)
 for entry in previous['images']:
  name=entry['export_filename'];old=(folder/name).resolve()
  if name not in names and old.parent==folder.resolve() and old.is_file():old.unlink()
 index.write_text(json.dumps({'count':len(files),'images':mapping},indent=2))
 blob=buffer.getvalue();temp=exports/'homepage-gallery.zip.tmp';temp.write_bytes(blob);os.replace(temp,exports/'homepage-gallery.zip')
 return blob

def scan():
 m=load() if MAN.exists() else {'version':1,'next_project':1,'projects':{},'assets':{},'limitations':['Visual grouping is proposed from human-readable contact sheets; no embedding model is installed. Uncertain sites remain unassigned.','UI elements require visual review; black-border detection does not remove toolbars.']}
 paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() in EXT and not any(x in p.relative_to(ROOT).parts for x in ['portfolio','.venv','.git','node_modules','organiser']))
 known={a['original_path'] for a in m['assets'].values()}; hashes={a['source_hash']:a.get('preferred_version',a['id']) for a in m['assets'].values()}
 for p in paths:
  rel=str(p.relative_to(ROOT))
  if rel in known:continue
  sha=digest(p);aid='image-'+hashlib.sha256(rel.encode()).hexdigest()[:12]
  a={'id':aid,'original_path':rel,'original_filename':p.name,'source_hash':sha,'project_id':None,'review_status':'pending','duplicate_status':'exact' if sha in hashes else 'unique','preferred_version':hashes.get(sha,aid),'duplicate_candidates':[],'quality_observations':[]}
  try:
   a.update(exif_metadata(p));im=read(p);crop=crop_proposal(im);x,y,r,b=crop['box'];clean=im[y:b,x:r];a.update(original_dimensions=[im.shape[1],im.shape[0]],crop=crop,perceptual_hash=str(dhash(clean)))
   if crop['applied']:a['quality_observations'].append('Screenshot padding detected; inspect remaining UI and crop before approval')
   if im.shape[0]/im.shape[1]>2:a['quality_observations'].append('Tall screenshot: inspect for interface elements and rotation')
   if min(clean.shape[:2])<700:a['quality_observations'].append('Limited usable resolution')
  except Exception as e:a['error']=str(e)
  a['screenshot_review_required']=bool(a.get('original_dimensions') and a['original_dimensions'][1]/a['original_dimensions'][0]>2)
  m['assets'][aid]=a; hashes.setdefault(sha,aid)
 assets=[a for a in m['assets'].values() if not a.get('error')]
 # Descriptor matches supplement hashes for screenshot/original and crop variants.
 # They only generate review candidates, never exclusions or site assignments.
 cv2.setNumThreads(2)
 detector=cv2.ORB_create(nfeatures=650);features={}
 for a in assets:
  im=read(ROOT/a['original_path']);x,y,r,b=a['crop']['box']
  if a['crop']['applied'] and a['crop']['decision']!='rejected':im=im[y:b,x:r]
  a['processed_dimensions']=[im.shape[1],im.shape[0]]
  a['perceptual_hash']=str(dhash(im));gray=cv2.cvtColor(resize(im,800),cv2.COLOR_BGR2GRAY)
  kp,des=detector.detectAndCompute(gray,None);features[a['id']]=(kp,des,gray.shape)
 matcher=cv2.BFMatcher(cv2.NORM_HAMMING)
 for i,a in enumerate(assets):
  for b in assets[i+1:]:
   if a['source_hash']==b['source_hash']:continue
   dist=bin(int(a['perceptual_hash'])^int(b['perceptual_hash'])).count('1');method=None
   if dist<=CONFIG['near_duplicate_distance']:method='difference hash'
   else:
    ka,da,sa=features[a['id']];kb,db,sb=features[b['id']]
    if da is not None and db is not None and min(len(da),len(db))>=30:
     pairs=matcher.knnMatch(da,db,k=2);good=[row[0] for row in pairs if len(row)==2 and row[0].distance<.7*row[1].distance]
     if len(good)>=30:
      src=np.float32([ka[v.queryIdx].pt for v in good]);dst=np.float32([kb[v.trainIdx].pt for v in good])
      transform,mask=cv2.findHomography(src,dst,cv2.RANSAC,3)
      if transform is not None and mask is not None and mask.sum()>=25 and mask.mean()>=.8:
       inside=mask.ravel().astype(bool)
       coverages=[np.prod(np.ptp(points[inside],axis=0))/(shape[0]*shape[1]) for points,shape in [(src,sa),(dst,sb)]]
       if min(coverages)>.3:method='geometric feature match; confirm same viewpoint'
   if method:
    preferred=max([a,b],key=lambda v:(np.prod(v.get('processed_dimensions',v['original_dimensions'])),not v.get('screenshot_review_required',False)))['id']
    for v,other in [(a,b),(b,a)]:
     candidate={'id':other['id'],'distance':dist,'method':method,'status':'needs-review','suggested_preferred_version':preferred}
     old=next((c for c in v['duplicate_candidates'] if c['id']==other['id']),None)
     if old:old.update(candidate)
     else:v['duplicate_candidates'].append(candidate)
 render(m);return m

def qa(m):
 errors=[]
 for a in m['assets'].values():
  if not (ROOT/a['original_path']).is_file() or digest(ROOT/a['original_path'])!=a['source_hash']:errors.append('Original changed: '+a['id'])
  for k in ['cleaned_path','web_path','thumbnail_path']:
   if not a.get('error') and not (OUT/a[k]).is_file():errors.append('Missing '+k+': '+a['id'])
 report={'source_images':len(m['assets']),'unique_file_contents':len(set(a['source_hash'] for a in m['assets'].values())),'projects':len(m['projects']),'exact_duplicates':sum(a['duplicate_status']=='exact' for a in m['assets'].values()),'crop_proposals':sum(a.get('crop',{}).get('applied',False) for a in m['assets'].values()),'near_duplicate_candidate_pairs':sum(len(a.get('duplicate_candidates',[])) for a in m['assets'].values())//2,'unassigned':sum(a['project_id'] is None for a in m['assets'].values()),'errors':errors,'limitations':m['limitations'],'manual_checks_remaining':['Confirm each proposed site grouping','Review crop boundaries and screenshot toolbars','Confirm near-duplicate matches; no uncertain match is excluded automatically','Confirm category and content assessment before marking ready']}
 (OUT/'reports/qa.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['scan','qa']);args=parser.parse_args();m=scan() if args.command=='scan' else load();print(json.dumps(qa(m),indent=2))
