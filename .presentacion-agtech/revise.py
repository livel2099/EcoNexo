from pathlib import Path
r=Path(__file__).parent
s=(r/'build.mjs').read_text(encoding='utf-8')
s=s.replace("function text(s,t,x,y,w,h,size=30,color=C.ink,bold=false){", "function text(s,t,x,y,w,h,size=30,color=C.ink,bold=false){if(!s.addingCapture && [3,5,6,7,8,10].includes(s.number) && y>=235)return;")
s=s.replace('s.light=light;', 's.light=light;s.number=n;')
insert='''
const shots=[
 [3,'ag-ficha.png',[.035,.235,.06,.47],'Tu lote, con contexto','Cultivo, superficie y señales para preparar la recorrida.'],
 [5,'ag-avisos.png',[.035,.41,.06,.17],'Avisos para planificar','Condiciones a revisar antes de organizar una labor.'],
 [6,'ag-pronostico.png',[.035,.285,.06,.165],'Los próximos días','Lluvia y demanda del cultivo para seguir el agua del lote.'],
 [7,'ecocampo-forraje.png',[.065,.105,.10,.16],'Un cálculo que se puede revisar','Mediciones de forraje y demanda animal como base de la planificación.'],
 [8,'ecocampo-historial.png',[.04,.35,.065,.14],'Cada evaluación deja un registro','Fecha, resultado y datos pendientes para la siguiente revisión.'],
 [10,'ag-resumen.png',[.025,.105,.06,.30],'Empezar con una decisión propia','Un lote y una necesidad concreta para evaluar la utilidad de Econexo.']
];
for(const [n,file,edges,head,body] of shots){const sl=p.slides.items[n-1];sl.addingCapture=true;const col=sl.light?C.dark:C.ink;text(sl,head,64,275,430,110,38,sl.light?C.dark:C.green,true);text(sl,body,64,420,420,150,29,col);const b=await fs.readFile(path.join(build,'capturas',file));sl.images.add({blob:b,contentType:'image/png',alt:'Captura de la interfaz Econexo con datos de demostración',fit:'contain',position:{left:535,top:250,width:680,height:360},crop:{left:edges[0],top:edges[1],right:edges[2],bottom:edges[3]}});text(sl,'Interfaz de Econexo con datos de demostración',535,635,680,30,18,sl.light?C.dark:C.muted);sl.speakerNotes.text+='\\n\\nEN PANTALLA: '+head+'. '+body+' Aclarar que los valores son ejemplos de demostración y no resultados reales de un establecimiento.';}
await fs.writeFile(path.join(build,'guion.json'),JSON.stringify(p.slides.items.map((sl,i)=>({number:i+1,notes:sl.speakerNotes.text})),null,2));
'''
s=s.replace("await (await PresentationFile.exportPptx(p)).save",insert+"\nawait (await PresentationFile.exportPptx(p)).save",1)
s=s.replace("'draft.pptx'","'draft-imagenes.pptx'").replace('`slide-${i+1}.png`','`visual-${i+1}.png`').replace("'Econexo_Jornada_Agtech.pptx'","'Econexo_Jornada_Agtech_con_Imagenes.pptx'").replace("'validation.json'","'validation-imagenes.json'")
(r/'build-imagenes.mjs').write_text(s,encoding='utf-8')
