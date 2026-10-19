from pathlib import Path
p=Path('apps/web/components/ParaguaySoyPanel.tsx');s=p.read_text(encoding='utf-8')
s=s.replace('polygon={polygon}/>', "polygon={polygon} onPolygon={p=>{setPolygon(p?JSON.stringify(p):'');setImage('');setSat(null);setReport(null);}}/>")
s=s.replace('<label>Límites del lote GeoJSON Polygon<textarea','<p>El contorno se dibuja en el paso Ubicación. También podés cargar sus coordenadas en las opciones avanzadas.</p><button onClick={()=>setTab(\'location\')}>Ir a dibujar mi lote</button><details><summary>Opciones avanzadas de coordenadas</summary><label>Límites del lote GeoJSON Polygon<textarea')
s=s.replace("placeholder='{\"type\":\"Polygon\",\"coordinates\":[[[lon,lat],...]]}'/></label><label>Capa", "placeholder='{\"type\":\"Polygon\",\"coordinates\":[[[lon,lat],...]]}'/></label></details><label>Capa")
p.write_text(s,encoding='utf-8')
p=Path('apps/web/app/dashboard/page.tsx');s=p.read_text(encoding='utf-8');a=s.index('        <button\n          type="button"\n          className="panel-pill banner-pill"');b=s.index('        </button>',a)+len('        </button>');s=s[:a]+s[b:];s=s.replace('hidden={!kpisOpen}>','>');p.write_text(s,encoding='utf-8')
