import React,{useEffect,useRef} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
const colors={planned:'#c78a2f',under_acquisition:'#487eb0',acquired:'#42825a',unknown:'#818b81'};
export default function ProjectMap({geometry,parcels}){
 const host=useRef(null);
 const features=geometry?.features||[];
 const located=parcels.filter(p=>p.latitude!==null&&p.longitude!==null);
 useEffect(()=>{
  if(!host.current||(!features.length&&!located.length))return;
  const map=L.map(host.current,{scrollWheelZoom:false,attributionControl:false});
  const group=L.featureGroup().addTo(map);
  function textPopup(text){const el=document.createElement('div');el.textContent=text;return el;}
  if(features.length)L.geoJSON({type:'FeatureCollection',features},{style:f=>({color:colors[f.properties.stage]||colors.unknown,weight:4,fillOpacity:.17,dashArray:f.properties.stage==='planned'?'8 6':null}),pointToLayer:(f,ll)=>L.circleMarker(ll,{radius:7,color:colors[f.properties.stage]||colors.unknown}),onEachFeature:(f,layer)=>layer.bindPopup(textPopup(`${f.properties.project_id} · ${f.properties.area_name||'Area not supplied'} · ${f.properties.stage}. Source: ${f.properties.source_reference}`))}).addTo(group);
  for(const p of located)L.circleMarker([p.latitude,p.longitude],{radius:6,color:'#254c3c',fillColor:'#e0eccc',fillOpacity:1}).bindPopup(textPopup(`Parcel ${p.parcel_id} · ${p.area_name} · ${p.acquisition_status}`)).addTo(group);
  map.fitBounds(group.getBounds(),{padding:[25,25],maxZoom:14});
  const timer=setTimeout(()=>map.invalidateSize(),50);
  const resize=new ResizeObserver(()=>map.invalidateSize());resize.observe(host.current);
  return()=>{clearTimeout(timer);resize.disconnect();map.remove()};
 },[geometry,parcels]);
 return <><div className="map-legend">{Object.entries(colors).map(([stage,color])=><span key={stage}><i style={{background:color}}/>{stage.replaceAll('_',' ')}</span>)}</div>{features.length||located.length?<div className="project-map" ref={host}/>:<div className="empty-module">No location evidence uploaded. Add parcel coordinates or a source-referenced project GeoJSON to display coverage.</div>}<p className="map-note">Offline coordinate map: {features.length} supplied geometry features and {located.length} located parcels. No background map or external tiles are requested. A planned line shows alignment; only uploaded polygons show stated coverage. Parcel points do not establish parcel boundaries or legal overlap.</p></>;
}
