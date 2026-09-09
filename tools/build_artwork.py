from pathlib import Path
import sys
base=Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'plugin'))
from artwork import portrait
out=base/'assets';out.mkdir(exist_ok=True)
font='font-family="DejaVu Sans, sans-serif"'
svg='<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 128 128"><rect width="128" height="128" rx="28" fill="#0b0c16"/>'+portrait()+'</svg>'
(out/'icon.svg').write_text(svg)
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">','<rect width="1600" height="900" fill="#0b0c16"/>',f'<text x="90" y="104" fill="#82fb9c" font-size="21" letter-spacing="5" {font}>WISP / MACHINE FAMILIAR</text>',f'<text x="90" y="170" fill="#ddf7ff" font-size="43" {font}>A small world. A character of your own.</text>',f'<text x="90" y="211" fill="#8196a0" font-size="19" {font}>Four lineages · sixteen forms · shaped by what you create</text>']
for row,(family,title) in enumerate([('Maker','FORGEWRIGHT'),('Artist','PRISMWEAVER'),('Musician','RESONANT'),('Archivist','LOREKEEPER')]):
 y=253+row*153
 s.append(f'<text x="90" y="{y+66}" fill="#82fb9c" font-size="16" letter-spacing="2" {font}>{title}</text>')
 for stage in range(4):
  x=390+stage*265
  s.append(f'<rect x="{x-15}" y="{y}" width="222" height="138" rx="15" fill="#121b22" stroke="#27363b"/>')
  s.append(f'<g transform="translate({x+40},{y-3}) scale(1.18)">{portrait(family,stage,17)}</g>')
for stage,label in enumerate(['SPARK','SPROUT','FAMILIAR','GUARDIAN']):s.append(f'<text x="{422+stage*265}" y="878" fill="#8196a0" font-size="13" letter-spacing="2" {font}>{label}</text>')
s.append('</svg>');(out/'lineages.svg').write_text(''.join(s))
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="760" viewBox="0 0 1600 760"><defs><radialGradient id="glow"><stop stop-color="#20453d"/><stop offset="1" stop-color="#0b0c16"/></radialGradient></defs><rect width="1600" height="760" fill="#0b0c16"/><circle cx="1180" cy="350" r="390" fill="url(#glow)"/>',f'<text x="110" y="139" fill="#82fb9c" font-size="19" letter-spacing="6" {font}>OMARCHY / A LOCAL COMPANION</text>',f'<text x="103" y="308" fill="#ddf7ff" font-size="148" font-weight="bold" {font}>Wisp</text>',f'<text x="110" y="388" fill="#b5cdd0" font-size="32" {font}>Let your machine grow a little soul.</text>',f'<text x="110" y="479" fill="#8196a0" font-size="23" {font}>Evolve. Roam. Remember. Dream.</text>',f'<text x="110" y="606" fill="#82fb9c" font-size="19" letter-spacing="2" {font}>NATIVE QML   /   LOCAL AI   /   YOUR THEME</text>',f'<g transform="translate(940,135) scale(3.8)">{portrait("Musician",2,17)}</g>','<path d="M110 660 H1490" stroke="#27363b"/>',f'<text x="110" y="707" fill="#8196a0" font-size="16" {font}>Created by 0xQuan · MIT licensed · No cloud required</text>','</svg>']
(out/'cover.svg').write_text(''.join(s))
