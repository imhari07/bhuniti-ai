import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import Community from './Community';
import './styles.css';
function Workspace(){const [page,setPage]=useState('analysis');return <><nav className="workspace-switch" aria-label="Workspace"><b>BhuNiti AI</b><button className={page==='analysis'?'':'secondary'} onClick={()=>setPage('analysis')}>Project analysis</button><button className={page==='community'?'':'secondary'} onClick={()=>setPage('community')}>Citizen & official portals</button></nav><div hidden={page!=='analysis'}><App/></div><div hidden={page!=='community'}><Community/></div></>}
createRoot(document.getElementById('root')).render(<React.StrictMode><Workspace/></React.StrictMode>);
