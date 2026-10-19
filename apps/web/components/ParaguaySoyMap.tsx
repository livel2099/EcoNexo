"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, LayerGroup } from "leaflet";

export default function ParaguaySoyMap({lat,lon,onSelect,polygon}:{lat:number;lon:number;onSelect:(lat:number,lon:number)=>void;polygon:object|null}) {
  const ref=useRef<HTMLDivElement>(null), map=useRef<LeafletMap|null>(null), layers=useRef<LayerGroup|null>(null);
  const [ready,setReady]=useState(false),[error,setError]=useState("");
  const select=useRef(onSelect);select.current=onSelect;
  const first=useRef(true);
  useEffect(()=>{let disposed=false;let resize:ResizeObserver|undefined;
    void (async()=>{const L=await import("leaflet");if(disposed||!ref.current)return;
      const m=L.map(ref.current).setView([-23.4,-58.4],6);map.current=m;
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(m);
      layers.current=L.layerGroup().addTo(m);m.on('click',e=>select.current(e.latlng.lat,e.latlng.lng));
      resize=new ResizeObserver(()=>m.invalidateSize());resize.observe(ref.current);
      try{const response=await fetch('/paraguay.geojson');if(!response.ok)throw Error();const geo=await response.json();if(!disposed){const boundary=L.geoJSON(geo,{style:{color:'#8ff06a',weight:2,fillOpacity:.05}}).addTo(m);m.fitBounds(boundary.getBounds(),{padding:[20,20]});}}
      catch{if(!disposed)setError('Límite territorial no disponible. El mapa base no es una imagen satelital.');}
      if(!disposed)setReady(true);
    })();return()=>{disposed=true;resize?.disconnect();map.current?.remove();map.current=null;};
  },[]);
  useEffect(()=>{let disposed=false;void import('leaflet').then(L=>{if(disposed||!ready||!map.current||!layers.current)return;layers.current.clearLayers();L.circleMarker([lat,lon],{color:'#33daff',radius:8}).addTo(layers.current);if(polygon){try{L.geoJSON(polygon as Parameters<typeof L.geoJSON>[0],{style:{color:'#33daff',fillOpacity:.12}}).addTo(layers.current);}catch{setError('No se pudo representar el polígono.');}}if(first.current)first.current=false;else map.current.panTo([lat,lon]);});return()=>{disposed=true;};},[lat,lon,polygon,ready]);
  return <><div ref={ref} className="py-soy-map" role="region" aria-label="Centro de Comando Paraguay"/>{error&&<p role="status">{error}</p>}<p className="muted">Paraguay · Natural Earth 1:10m, límite orientativo. Tocá el mapa o ingresá las coordenadas del lote. El polígono delimita la consulta satelital.</p></>;
}

