"""Build a self-contained read-only review site using only Python's standard library."""
from pathlib import Path
from html import escape
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'client-review'
TEMPLATE=ROOT/'organiser/client-review'
CATEGORIES={'domestic':'Domestic Scaffolding','commercial':'Commercial Scaffolding','temporary-roofs':'Temporary Roofs / False Roofs','needs-review':'Category to confirm'}

def retained(a):
 return not a.get('error') and a['review_status']!='unsuitable' and a['duplicate_status']!='exact' and a.get('duplicate_decision')!='duplicate'

def build():
 manifest=json.loads((ROOT/'portfolio/manifests/manifest.json').read_text())
 assets=[a for a in manifest['assets'].values() if retained(a)]
 if not assets:raise ValueError('There are no retained photos to publish')
 output_assets=OUT/'assets';output_assets.mkdir(parents=True,exist_ok=True)
 expected=set();photos=0;groups=0
 def copy_asset(relative,prefix):
  source=(ROOT/'portfolio'/relative).resolve()
  if not source.is_relative_to((ROOT/'portfolio').resolve()):raise ValueError('Invalid processed image path')
  if not source.is_file():raise ValueError('Missing processed image: '+relative)
  if source.suffix.lower()!='.webp':raise ValueError('Only processed WebP images belong in the review site')
  name=prefix+'-'+hashlib.sha256(source.read_bytes()).hexdigest()[:20]+'.webp'
  expected.add(name);destination=output_assets/name
  if not destination.exists():shutil.copyfile(source,destination)
  return 'assets/'+name
 def gallery(members,project=None):
  nonlocal photos,groups
  if not members:return ''
  groups+=1;pid=project['id'] if project else 'unassigned';title=project['title'] if project else 'Not yet grouped';hero=project.get('hero') if project else None
  members=sorted(members,key=lambda a:a['id']!=hero)
  cards=[]
  for index,a in enumerate(members,1):
   large=copy_asset(a['web_path'],'photo');thumb=copy_asset(a['thumbnail_path'],'thumb');photos+=1
   label=title+' — photo '+str(index);badges=[]
   if a['id']==hero:badges.append('<span class="badge hero">Hero image</span>')
   if a.get('homepage_selected'):badges.append('<span class="badge">Homepage shortlist</span>')
   cards.append(f'<figure class="photo" data-homepage="{str(bool(a.get("homepage_selected"))).lower()}"><a class="photo-link" href="{large}" data-caption="{escape(label,quote=True)}" aria-label="View {escape(label,quote=True)}"><img src="{thumb}" loading="lazy" decoding="async" alt="{escape(label,quote=True)}"></a><figcaption>{"".join(badges)}<span class="photo-number">Photo {index:02d}</span></figcaption></figure>')
  tags=project.get('secondary_categories',[]) if project else []
  tag_html='<p class="tags">'+escape(' · '.join(tags))+'</p>' if tags else ''
  return f'<section class="group" id="{escape(pid,quote=True)}" data-title="{escape(title.lower(),quote=True)}"><div class="group-heading"><h3>{escape(title)}</h3><span class="count">{len(members)} photos</span></div>{tag_html}<div class="photo-grid">{"".join(cards)}</div></section>'
 sections=[]
 for key,label in CATEGORIES.items():
  galleries=[]
  for project in manifest['projects'].values():
   if project['primary_category']!=key:continue
   body=gallery([a for a in assets if a['project_id']==project['id']],project)
   if body:galleries.append(body)
  if galleries:sections.append(f'<section class="category" data-category="{key}" id="category-{key}"><div class="category-heading"><p class="eyebrow">Portfolio category</p><h2>{escape(label)}</h2></div>{"".join(galleries)}</section>')
 unassigned=[a for a in assets if not a['project_id']]
 if unassigned:sections.append('<section class="category" data-category="unassigned" id="category-unassigned"><div class="category-heading"><p class="eyebrow">For discussion</p><h2>Not yet grouped</h2></div>'+gallery(unassigned)+'</section>')
 if photos!=len(assets):raise ValueError('Some retained photos have an unknown project or category; correct these before exporting')
 choices=''.join(f'<option value="{key}">{escape(label)}</option>' for key,label in CATEGORIES.items())
 if unassigned:choices+='<option value="unassigned">Not yet grouped</option>'
 homepage=sum(bool(a.get('homepage_selected')) for a in assets)
 html=(TEMPLATE/'index.html').read_text().replace('{{GALLERIES}}',''.join(sections)).replace('{{CATEGORY_OPTIONS}}',choices).replace('{{PHOTO_COUNT}}',str(photos)).replace('{{GROUP_COUNT}}',str(groups-int(bool(unassigned)))).replace('{{HOMEPAGE_COUNT}}',str(homepage))
 (OUT/'index.html').write_text(html)
 for name in ['style.css','review.js','robots.txt','_headers']:shutil.copyfile(TEMPLATE/name,OUT/name)
 # This directory is generated and contains only copied public review images.
 for path in output_assets.iterdir():
  if path.is_file() and path.name not in expected:path.unlink()
 size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
 print(json.dumps({'publish_directory':str(OUT.relative_to(ROOT)),'photos':photos,'groups':groups-int(bool(unassigned)),'unassigned':len(unassigned),'homepage_shortlist':homepage,'asset_files':len(expected),'total_bytes':size},indent=2))

if __name__=='__main__':build()
