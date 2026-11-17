const { chromium } = require('../apps/web/node_modules/@playwright/test');
(async () => {
  let browser;
  try { browser = await chromium.launch({headless:true}); }
  catch { browser = await chromium.launch({headless:true,channel:'msedge'}); }
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const session = {access_token:'local-test-only',org_id:'test',role:'admin',name:'Prueba',email:'test@example.invalid',avatar_url:null,auth_provider:'password'};
  const forecast = Array.from({length:7},(_,i)=>({day:'2026-11-'+String(17+i),tmax:30,tmin:21,precipitation_mm:4,et0_mm:5}));
  let contextCalls=0;
  await page.addInitScript(s=>sessionStorage.setItem('econexo_session',JSON.stringify(s)),session);
  await page.route('**/*', async route => {
    const u = new URL(route.request().url());
    if(u.hostname==='127.0.0.1' || u.hostname==='gibs.earthdata.nasa.gov' || u.hostname.endsWith('tile.openstreetmap.org')) return route.continue();
    let body=[];
    if(u.pathname==='/brasil/mato-grosso/alerts') body={queried_at:new Date().toISOString(),sources:[{source:'INPE de prueba',status:'ok',message:'Fixture local',features:[{type:'Feature',geometry:{type:'Polygon',coordinates:[[[-55.9,-12.6],[-55.6,-12.6],[-55.6,-12.4],[-55.9,-12.6]]]},properties:{id:'burn-test',kind:'burned',source:'INPE de prueba',observed_at:'2026-11-10',municipality:'Sorriso',municipality_code:'5107925',title:'Zona quemada · cicatriz DETER',status:'Prueba de interfaz'}}]}]};
    if(u.pathname==='/auth/me') body=session;
    if(u.pathname==='/orgs/me') body={id:'test',name:'Prueba local'};
    if(u.pathname==='/kpis') body={global_status:'normal'};
    if(u.pathname==='/environment/source-settings') body={default_latitude:-27.3,default_longitude:-55.9};
    if(u.pathname==='/brasil/mato-grosso/soja/context') {
      contextCalls++;
      body={queried_at:new Date().toISOString(),source:'Proveedor de prueba',timezone:'America/Cuiaba',variables:{},forecast,error:null,note:'Datos de prueba'};
    }
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto('http://127.0.0.1:4191/dashboard');
  await page.getByRole('button',{name:'Brasil · Mato Grosso',exact:true}).click();
  await page.getByRole('heading',{name:'Pronóstico para soja · próximos 7 días'}).waitFor();
  await page.getByRole('table').filter({has:page.getByText('Máxima °C',{exact:true})}).waitFor();
  if(!contextCalls) throw Error('No se consultó la ruta brasileña');
  await page.getByRole('button',{name:'3 Evaluación',exact:true}).click();
  await page.getByLabel('Nombre del lote',{exact:true}).fill('Lote Sorriso');
  await page.getByRole('button',{name:'Mapa estatal y alertas',exact:true}).click();
  await page.getByRole('heading',{name:'Monitoreo de Mato Grosso',exact:true}).waitFor();
  await page.getByRole('checkbox',{name:'Vegetación NDVI · NASA'}).check();
  await page.getByText('NDVI cargado.',{exact:false}).waitFor({timeout:35000});
  await page.getByRole('button',{name:'Ver zonas quemadas',exact:true}).click();
  if(await page.getByLabel('Tipo de alerta').inputValue()!=='burned') throw Error('Filtro quemadas no aplicado');
  await page.getByText('Zona quemada · cicatriz DETER',{exact:true}).waitFor();
  await page.locator('#mato-grosso-map').screenshot({path:'tmp/codex-brasil-ndvi-map.png'});
  await page.getByRole('button',{name:'Soja · pronóstico y evaluación',exact:true}).click();
  if(await page.getByLabel('Nombre del lote',{exact:true}).inputValue()!=='Lote Sorriso') throw Error('Se perdieron los datos del lote');
  if(errors.length) throw Error(errors.join('\n'));
  console.log('OK: NDVI real NASA cargado, filtro de zonas quemadas y persistencia del lote verificados.');
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
