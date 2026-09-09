"""Original portraits rendered from the same pixel silhouettes as the QML companion."""
import json, math, re
from pathlib import Path

def forms():
 text=(Path(__file__).parent/'Forms.js').read_text().split('var families = ',1)[1].split('\nfunction rows',1)[0]
 return json.loads(re.sub(r'(?m)^(Maker|Artist|Musician|Archivist):',r'"\1":',text))
def portrait(family='Musician',level=2,seed=0,accent='#82fb9c',foreground='#ddf7ff',background='#0b0c16'):
 rows=forms()[family][level]
 pixels=[]
 for y,row in enumerate(rows):
  for x,value in enumerate(row):
   if value!='0':pixels.append(f'<rect x="{32+x*4}" y="{14+y*4}" width="3.8" height="3.8" fill="{accent}" opacity="{0.38 if value=="2" else 0.88}"/>')
 for mark in range(3):pixels.append(f'<rect x="{49+((seed>>(mark*3))%7)*4}" y="{22+mark%2*4}" width="3" height="2" fill="{foreground}" opacity=".55"/>')
 pixels += [f'<rect x="{x}" y="42" width="7" height="6" fill="{background}"/>' for x in [49,72]]
 pixels.append(f'<rect x="61" y="54" width="6" height="2" fill="{background}"/>')
 pixels.append(f'<ellipse cx="64" cy="94" rx="52" ry="9" fill="none" stroke="{accent}" opacity=".45"/>')
 for j in range(12):
  angle=j*math.pi/6;pixels.append(f'<rect x="{63+math.cos(angle)*50:.2f}" y="{94+math.sin(angle)*8:.2f}" width="3" height="3" fill="{accent}" opacity=".7"/>')
 return ''.join(pixels)
def export(profile,growth,palette):
 from identity import appearance
 from growth import STATE,put
 palette={k:(v if re.fullmatch(r'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?',str(v)) else '#101817') for k,v in palette.items()}
 look=appearance(profile,growth.get('traits',{}))
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 128 128"><rect width="128" height="128" rx="28" fill="{palette["background"]}"/>'+portrait(look['family'],growth.get('level',0),profile['seed'],palette['accent'],palette['foreground'],palette['background'])+'</svg>'
 path=STATE/'portrait.svg';path.write_text(svg);path.chmod(0o600);return str(path)
