"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, LayerGroup } from "leaflet";

export default function ParaguaySoyMap({lat,lon,onSelect,polygon,onPolygon}:{lat:number;lon:number;onSelect:(lat:number,lon:number)=>void;polygon:object|null;onPolygon?:(polygon:object|null)=>void}) {
  const ref=useRef<HTMLDivElement>(null), map=useRef<LeafletMap|null>(null), layers=useRef<LayerGroup|null>(null);
  const [ready,setReady]=useState(false),[error,setError]=useState("");
  const select=useRef(onSelect);select.current=onSelect;
  const first=useRef(true);
  const [drawing,setDrawing]=useState(false),[points,setPoints]=useState<[number,number][]>([]);
  const drawingRef=useRef(false);drawingRef.current=drawing;
  useEffect(()=>{let disposed=false;let resize:ResizeObserver|undefined;
    void (async()=>{const L=await import("leaflet");if(disposed||!ref.current)return;
      const m=L.map(ref.current).setView([-23.4,-58.4],6);map.current=m;
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(m);
      layers.current=L.layerGroup().addTo(m);m.on('click',e=>{if(drawingRef.current)setPoints(p=>[...p,[e.latlng.lng,e.latlng.lat]]);else select.current(e.latlng.lat,e.latlng.lng);});
      resize=new ResizeObserver(()=>m.invalidateSize());resize.observe(ref.current);
      try{const response=await fetch('/paraguay.geojson');if(!response.ok)throw Error();const geo=await response.json();if(!disposed){const boundary=L.geoJSON(geo,{style:{color:'#8ff06a',weight:2,fillOpacity:.05}}).addTo(m);m.fitBounds(boundary.getBounds(),{padding:[20,20]});}}
      catch{if(!disposed)setError('Límite territorial no disponible. El mapa base no es una imagen satelital.');}
      if(!disposed)setReady(true);
    })();return()=>{disposed=true;resize?.disconnect();map.current?.remove();map.current=null;};
  },[]);
  useEffect(()=>{let disposed=false;void import('leaflet').then(L=>{if(disposed||!ready||!map.current||!layers.current)return;layers.current.clearLayers();L.circleMarker([lat,lon],{color:'#177f70',radius:8}).addTo(layers.current);if(drawing&&points.length){L.polyline(points.map(([x,y])=>[y,x] as [number,number]),{color:'#177f70',weight:3}).addTo(layers.current);points.forEach(([x,y])=>L.circleMarker([y,x],{radius:4,color:'#177f70'}).addTo(layers.current!));}else if(polygon){try{L.geoJSON(polygon as Parameters<typeof L.geoJSON>[0],{style:{color:'#177f70',fillOpacity:.12}}).addTo(layers.current);}catch{setError('No se pudo representar el polígono.');}}if(first.current)first.current=false;});return()=>{disposed=true;};},[lat,lon,polygon,ready,drawing,points]);
  return <>{onPolygon&&<div className="workspace-map-tools">{drawing?<><p role="status">Marcá las esquinas del lote en el mapa. {points.length} puntos.</p><button disabled={points.length<3} onClick={()=>{const ring=[...points,points[0]];onPolygon({type:'Polygon',coordinates:[ring]});onSelect(points[0][1],points[0][0]);setDrawing(false);setPoints([]);}}>Guardar contorno</button><button onClick={()=>{setDrawing(false);setPoints([]);}}>Cancelar dibujo</button></>:<><button onClick={()=>{setPoints([]);setDrawing(true);}}>Dibujar límites del lote</button>{polygon&&<button onClick={()=>onPolygon(null)}>Borrar contorno</button>}<span>{polygon?'Contorno listo para consultar el satélite':'Opcional: dibujá el contorno para habilitar la consulta satelital.'}</span></>}</div>}<div ref={ref} className="py-soy-map" role="region" aria-label="Centro de Comando Paraguay"/>{error&&<p role="status">{error}</p>}<p className="muted">Paraguay · Natural Earth 1:10m, límite orientativo. Tocá el mapa o ingresá las coordenadas del lote. Para dibujar, acercá el mapa hasta identificar los límites reales de tu campo.</p></>;
}

