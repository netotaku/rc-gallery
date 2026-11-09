"""One-time proposals from visual contact-sheet inspection, never filename/date clustering."""
from workflow import *
def seed():
 m=load()
 if m.get('visual_seed_applied'):return
 inventory=json.loads((OUT/'reports/initial-inventory.json').read_text());byname={a['original_filename']:a for a in m['assets'].values()}
 groups=[
 ([1,2,17],'domestic','Rendered House Roof Access','Matching rendered gables, tiled roof, chimney and central scaffold bay. Confirm screenshot association.', 'medium',['Roof access scaffolding']),
 ([7,20,101,102,103],'domestic','Stone Building Facade Access','Matching honey-coloured stone facade, tall window bays and scaffold arrangement; screenshot includes gallery interface. Building use requires confirmation.','medium',['Renovation and refurbishment access']),
 ([8,104,105,107,108],'temporary-roofs','Temporary Roof Over Stone Structure','Aerial views show a scaffold enclosure over a stone structure; interior photographs show roof trusses and striped roof covering. Confirm interior-to-exterior association.','medium',[]),
 ([11,12,13,14,15,16],'needs-review','Gabled Stone Building Roof Access','Repeated stone gable, distinctive circular gable detail, white window frames, front hedge and matching scaffold. Building use requires confirmation.','high',['Roof access scaffolding']),
 ([33,34,47,112,115],'temporary-roofs','Wrapped Roof Scaffold Above Stone Walls','Matching exposed stone end wall, scaffold bracing, white upper enclosure and surrounding garden.','high',[]),
 ([52,53,54],'needs-review','Clock Turret Roof Access','Matching red tiled turret, clock face, low adjacent roof and scaffold decking. Building use requires confirmation.','high',['Roof access scaffolding']),
 ([96,97],'needs-review','Rendered Building Opening Support','Matching pale rendered facade, upper window and scaffold at the opening. Scope and site use need confirmation.','high',[]),
 ([88,89],'needs-review','Aerial Scaffold Site Views','Matching aerial site footprint, white structure, surrounding trees and material storage. Category and service scope need confirmation.','high',[]),
 ([99,100],'needs-review','Low Level Construction Access','Matching site ground, roofline, chimney and blue-sky viewpoint; verify the association before approval.','medium',[]),
 ([74,75,76,77,78,79],'needs-review','Stone Corner Building Upper Access','Matching stone corner elevations, cornice and upper scaffold platforms seen from multiple viewpoints. Verify each elevation and building use.','medium',['Roof access scaffolding']),
 ([6,32,113],'needs-review','Long Stone Frontage Access','Matching low stone frontage, street kerb, roof forms and scaffold run.','medium',['Renovation and refurbishment access'])]
 groups += [
 ([31,38,43],'needs-review','Ornate Gabled Street Frontage','Matching decorative gables, chimney arrangement, frontage windows and overhead street lighting. Building use requires confirmation.','high',[]),
 ([36,37,45,46,48],'domestic','Brick House Upper Roof Access','Matching red brick house, contrasting upper render, pitched tiled roof and elevated scaffold platform.','high',['Roof access scaffolding']),
 ([41,42],'domestic','Brick Building Roof Framework Access','Matching brick elevation, windows, scaffold poles and roof framework seen along the same wall.','high',['Roof access scaffolding']),
 ([51,55],'needs-review','Long Brick Elevation Access','Matching long brick wall, yellow door, roof detail and boundary wall along the access path. Confirm building use.','high',['Renovation and refurbishment access']),
 ([65,66,67],'domestic','House Roof Platform Scaffold','Matching domestic gabled entrance, tiled roof, scaffold canopy and upper platform arrangement.','high',['Roof access scaffolding']),
 ([68,69,70,72,73],'temporary-roofs','Temporary Roof Construction Views','Roof trusses, extensive scaffold framework and corrugated roof panels; wider landscape and roof arrangement suggest one installation, requiring confirmation.','medium',[]),
 ([35,60],'domestic','Brick Terrace Frontage Access','Matching brick frontage, white window bays, scaffold run and front boundary.','medium',['Renovation and refurbishment access']),
 ([24,25],'needs-review','Interior Structural Support Installation','Red support frames under exposed floor beams and matching pale interior finishes. Confirm shared site and exact support service with Redcatch.','medium',[])
 ]
 for nums,cat,title,evidence,confidence,tags in groups:
  pid=new_project(m,cat,title,evidence,confidence);p=m['projects'][pid];p['secondary_categories']=tags
  p['content_assessment']['potential_relevance']='Promising visual evidence for a portfolio entry; confirm site identity, building use and scope before content development.'
  for n in nums:
   a=byname[inventory[n-1]['name']]
   if a['project_id'] is None:a['project_id']=pid
 m['visual_seed_applied']=True
 m['limitations'][0]='Initial groups were proposed through image-capable visual inspection of contact sheets. No embedding model is installed; no automatic cross-viewpoint site clustering is claimed. New images remain unassigned.'
 render(m);print(json.dumps(qa(m),indent=2))
if __name__=='__main__':seed()
