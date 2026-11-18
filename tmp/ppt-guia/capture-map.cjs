const {chromium}=require('../../apps/web/node_modules/playwright');
const path=require('path');
(async()=>{
 const b=await chromium.launch({channel:'chrome'});const p=await b.newPage({viewport:{width:1440,height:1000}});
 await p.goto('http://localhost:3110/login/');
 await p.getByRole('button',{name:'Solo esenciales',exact:true}).click();
 await p.getByRole('button',{name:'Ingresar',exact:true}).click();
 await p.getByRole('button',{name:/Abrir Brasil/}).click({timeout:45000});
 await p.getByRole('button',{name:'Português',exact:true}).click();
 await p.getByRole('button',{name:'1 Localização',exact:true}).click();
 await p.locator('.leaflet-overlay-pane path').first().waitFor({state:'visible',timeout:30000});
 await p.locator('.leaflet-container').first().screenshot({path:path.join(__dirname,'localizacao.png')});
 await b.close();
})().catch(e=>{console.error(e);process.exitCode=1});
