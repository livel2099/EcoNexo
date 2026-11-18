"use client";
import {useEffect,useRef} from 'react';
import type {Geometry} from 'geojson';
import {useBrazilLanguage} from './BrazilLanguage';

export default function BrazilParcelMap({geometry}:{geometry:Geometry}) {
 const host=useRef<HTMLDivElement>(null);
 const {language}=useBrazilLanguage();
 useEffect(()=>{let disposed=false;let map:import('leaflet').Map|undefined;let observer:ResizeObserver|undefined;
  void import('leaflet').then(L=>{if(disposed||!host.current)return;
   map=L.map(host.current);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:18}).addTo(map);
   const layer=L.geoJSON(geometry,{style:{color:'#8ff06a',weight:2,fillOpacity:.12}}).addTo(map);
   map.fitBounds(layer.getBounds(),{padding:[20,20]});observer=new ResizeObserver(()=>map?.invalidateSize());observer.observe(host.current);
  });return()=>{disposed=true;observer?.disconnect();map?.remove();};
 },[geometry]);
 return <div ref={host} className="py-soy-map" style={{height:340}} role="region" aria-label={language==='pt'?'Limites do talhão':'Límites del lote'}/>;
}
