import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1117-1425-0_26.1117.1425.0_x64__3k8sg7r9htsxt/dependencies';
const {Presentation,PresentationFile}=await import(pathToFileURL(ROOT+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
const dir=path.dirname(fileURLToPath(import.meta.url));
const workspace=path.resolve(dir,'../..');
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#12382F',green:'#17694E',light:'#F4F5EF',muted:'#52675E',lime:'#B7EF80',white:'#FFFFFF'};
function text(s,str,x,y,w,h,size=26,color=C.ink,bold=false){
 const el=s.shapes.add({geometry:'textbox',name:str.slice(0,40),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 el.text=str;el.text.style={fontFamily:'Arial',fontSize:size,color,bold};return el;
}
function slide(title,notes,dark=false){
 const s=p.slides.add();s.background.fill=dark?C.ink:C.light;
 text(s,title,64,51,1152,114,44,dark?C.white:C.ink,true);
 text(s,'ECONEXO',64,667,1040,25,17,dark?C.lime:C.green,true);
 text(s,String(p.slides.items.length).padStart(2,'0'),1160,667,56,25,17,dark?C.lime:C.muted);
 s.speakerNotes.text=notes;return s;
}
function steps(s,items,x=66,y=200,w=370,gap=130){
 items.forEach((a,i)=>{text(s,String(i+1).padStart(2,'0'),x,y+i*gap,50,40,24,C.green,true);text(s,a,x+58,y+i*gap,w-58,gap-12,25);});
}
async function screenshot(s,file,alt){s.images.add({blob:new Uint8Array(await fs.readFile(path.join(dir,file+'.png'))),contentType:'image/png',alt,fit:'contain',position:{left:475,top:180,width:741,height:462}});text(s,'Tela de demonstração. A disponibilidade de dados depende das conexões.',475,637,741,28,14,C.muted);}
function pair(s,left,right){
 text(s,left[0],66,193,520,70,29,C.green,true);text(s,left[1],66,280,520,330,28);
 text(s,right[0],688,193,520,70,29,C.green,true);text(s,right[1],688,280,520,330,28);
}
let s=p.slides.add();s.background.fill=C.ink;
text(s,'ECONEXO',72,70,1000,60,34,C.lime,true);
text(s,'Guia de uso\nda plataforma',72,210,1120,210,76,C.white,true);
text(s,'Português do Brasil\nPercurso para produtores e equipes técnicas',76,485,1100,100,28,'#DBE8DE');
text(s,'Brasil / Mato Grosso',76,645,1000,32,20,C.lime);
s.speakerNotes.text='Guia baseado na versão local da Econexo revisada em 18/11/2026. O percurso principal aborda Brasil, Mato Grosso e soja. A navegação geral ainda contém rótulos em espanhol. As capturas mostram o modo de demonstração, sem comprovar disponibilidade de dados operacionais. Fontes: apps/web/app/dashboard/page.tsx e apps/web/components/BrazilPanel.tsx.';

s=slide('O que você encontra na Econexo','Fontes: apps/web/components/WorkspaceHome.tsx e apps/web/app/dashboard/page.tsx. Os módulos têm escopos territoriais diferentes. A disponibilidade depende de acesso, licença e integrações.');
pair(s,['Uso agrícola','Brasil e Paraguai: avaliação de soja por talhão.\n\nMis cultivos: acompanhamento de áreas agrícolas.\n\nCampo y forraje: terreno e planejamento de forragem.'],['Monitoramento territorial','Mapa y alertas: acompanhamento em Misiones.\n\nInformes: documentos técnicos de Misiones.\n\nMais ferramentas: dispositivos, avisos cidadãos e configuração.']);

s=slide('Acesso à plataforma','Fonte: apps/web/components/AuthGateway.tsx e captura local /login. A conta de demonstração aparece na captura. Não usar credenciais de demonstração para operação real. Alguns recursos exigem licença e permissões.');
steps(s,['Acesse o endereço fornecido pela sua organização.','Informe e-mail e senha e clique em “Ingresar”.','Confira a organização e o perfil da conta ao entrar.']);
await screenshot(s,'login','Tela de acesso da Econexo em modo de demonstração');

s=slide('Página inicial e navegação','Fontes: apps/web/components/WorkspaceHome.tsx e apps/web/app/dashboard/page.tsx. Os totais da página inicial se referem a Misiones. Os rótulos do menu geral continuam em espanhol nesta versão.');
steps(s,['Escolha a tarefa na página inicial ou no menu lateral.','Para o percurso deste guia, abra “Brasil · Mato Grosso”.','Use “Volver al inicio” para retornar à página inicial.']);
await screenshot(s,'home','Página inicial com módulos e navegação lateral');

s=slide('Idioma da seção Brasil','Fontes: apps/web/components/BrazilLanguage.tsx e BrazilPanel.tsx. A preferência é guardada no navegador quando o armazenamento está disponível. O formulário mantém seus valores durante a troca de idioma. A tradução se aplica à seção Brasil e seus relatórios, não a toda a aplicação.');
pair(s,['Español / Português','Na seção Brasil, selecione “Português”.\n\nA plataforma mantém os dados já preenchidos durante a troca.\n\nO navegador lembra a preferência.'],['Alcance da tradução','As etapas de soja, os mapas e os relatórios seguem o idioma escolhido.\n\nNomes dos talhões e observações do produtor permanecem no idioma original.\n\nO menu geral pode exibir rótulos em espanhol.']);

s=slide('1. Localização do talhão','Fontes: apps/web/components/BrazilSoyPanel.tsx e BrazilSoyMap.tsx. A posição inicial é Sorriso, Mato Grosso, apenas como referência. Para desenho: selecionar Desenhar limites do talhão, marcar pelo menos três vértices e Salvar contorno. O sistema fecha o polígono. Os limites do mapa são orientativos.');
steps(s,['Em “Localização”, toque no mapa ou informe latitude e longitude.','Aproxime o mapa até identificar a área de interesse.','Para usar o satélite, desenhe os limites e salve o contorno.']);
await screenshot(s,'localizacao','Mapa de localização do talhão em Mato Grosso');

s=slide('2. Clima dos próximos sete dias','Fontes: apps/web/components/BrazilSoyPanel.tsx e apps/api/app/brazil_soy_context.py. Consulta Open-Meteo com alternativa MET Norway quando disponível. Temperatura, umidade do solo e previsão são estimativas de modelos. Campos vazios não equivalem a zero. A captura de demonstração não possui consulta operacional.');
steps(s,['Confira se as coordenadas correspondem ao seu talhão.','Clique em “Atualizar dados automáticos”.','Revise temperatura, chuva, data da consulta e dados ausentes.']);
await screenshot(s,'clima','Etapa Clima e orientação para atualizar os dados automáticos');

s=slide('3. Dados e observações de campo','Fontes: apps/web/components/BrazilSoyPanel.tsx e apps/api/app/brazil_soy.py. Preencher nome, área, data de observação, cultivar e estádio. As perguntas abrangem pH, solo, drenagem, água, compactação, erosão, sementes, nodulação e sanidade. Registrar a origem das medições. Não inventar dados para completar o formulário.');
steps(s,['Informe nome, área e data da observação do talhão.','Preencha cultivar, estádio e as condições que você verificou.','Deixe o desconhecido em branco e registre a origem das medições.']);
await screenshot(s,'avaliacao','Formulário de avaliação com um talhão de exemplo');

s=slide('4. Observação por satélite','Fontes: apps/web/components/BrazilSoyPanel.tsx e BrazilSoyMap.tsx. A consulta usa Sentinel-2 L2A dos últimos 30 dias e requer limites do talhão e Copernicus configurado. A composição pode combinar datas e conter nuvens ou ausência de cobertura. NDVI não diagnostica doenças nem mede produtividade.');
steps(s,['Confirme o contorno desenhado na etapa “Localização”.','Escolha cor natural, vegetação NDVI ou índice de umidade.','Clique em “Consultar imagem e NDVI” e confira a cobertura.']);
await screenshot(s,'satelite','Opções de imagem de satélite e NDVI');

s=slide('Leitura da avaliação de soja','Fontes: apps/api/app/brazil_soy.py e apps/api/app/routers/brazil_soy.py. A classificação depende da evidência fornecida, dos dados faltantes e dos riscos ativados. O método não certifica aptidão, rendimento ou rentabilidade. Recomendações exigem validação agronômica local.');
text(s,'Dados insuficientes',66,190,480,52,31,C.green,true);text(s,'Faltam evidências para uma leitura mais completa. Revise os campos pendentes.',560,190,642,83,27);
text(s,'Condicionado por riscos',66,328,480,52,31,C.green,true);text(s,'Há fatores que exigem atenção. Leia o motivo e a ação recomendada.',560,328,642,83,27);
text(s,'Potencial favorável preliminar',66,466,480,88,31,C.green,true);text(s,'A evidência disponível não ativou os riscos previstos pelo método. Confirme a decisão com seu assessor.',560,466,642,120,27);

s=slide('5. Relatórios e download','Fonte: apps/web/components/BrazilSoyPanel.tsx. Avaliar soja e consultar previsão gera a avaliação. Gerar e salvar relatório aparece para admin e operador. O download é um arquivo HTML para abrir no navegador, imprimir ou salvar como PDF. O idioma do download acompanha o seletor. Os relatórios históricos preservam evidência e previsão originais.');
pair(s,['Gerar e revisar','Clique em “Avaliar soja e consultar previsão”.\n\nEm “Relatórios”, confira riscos, dados pendentes e recomendações.\n\nAdministradores e operadores podem gerar e salvar o relatório da organização.'],['Baixar e compartilhar','Use “Baixar relatório para imprimir ou salvar como PDF”.\n\nAbra o arquivo HTML no navegador e escolha Imprimir / Salvar como PDF.\n\nAtualize o levantamento antes de uma nova decisão.']);

s=slide('Mapa estadual de Mato Grosso','Fonte: apps/web/components/BrazilMonitoringPanel.tsx. O seletor de município aproxima o mapa. A consulta meteorológica exige clicar em um ponto do território e representa esse ponto, não a média municipal ou estadual. O mapa usa limites simplificados do IBGE e base OpenStreetMap.');
steps(s,['Abra “Mapa estadual e alertas”.','Selecione o município ou use “Ver todo o estado”.','Toque em um ponto do território para consultar a previsão local.']);
await screenshot(s,'territorio','Mapa de municípios de Mato Grosso');

s=slide('Alertas e camadas de vegetação','Fontes: apps/web/components/BrazilAlerts.tsx, BrazilNdviLayer.tsx e apps/api/app/routers/brazil.py. Focos de calor: últimos dois dias. DETER: observações dos últimos 30 dias em Amazônia e Cerrado, sem garantia de cobertura do Pantanal. As fontes podem estar incompletas. A camada MODIS tem resolução nominal de 250 m e composição de oito dias. Os alertas aparecem na tela, sem envio externo automático neste módulo.');
pair(s,['Alertas por verificar','Filtre focos de calor, desmatamento ou áreas queimadas.\n\nConfira fonte, data e disponibilidade. Use “Ver no mapa” para localizar o aviso.\n\nUm foco de calor exige verificação em campo.'],['Vegetação NDVI da NASA','Ative a camada e selecione uma data disponível.\n\nAjuste a opacidade para comparar com o mapa.\n\nA camada mostra vegetação regional. Use Sentinel-2 para observar o talhão.']);

s=slide('Outras ferramentas da organização','Fontes: apps/web/app/dashboard/page.tsx, components/DevicesPanel.tsx, ReportsPanel.tsx e ImpactReportsPanel.tsx. Os módulos e ações visíveis dependem do perfil e da configuração. O painel de informes técnicos consolida exclusivamente dados de Misiones. Os relatórios de soja de Mato Grosso permanecem no módulo Brasil.');
pair(s,['Operação de campo','“Mis cultivos”: cadastro e acompanhamento agrícola.\n\n“Campo y forraje”: avaliação do terreno e planejamento.\n\n“Reportes ciudadanos”: revisão dos avisos recebidos.'],['Equipe e administração','“Dispositivos”: fontes de medição da organização.\n\n“Configuración”: acesso e parâmetros disponíveis ao administrador.\n\n“Informes”: documentos técnicos de Misiones.']);

s=slide('Rotina recomendada de uso','Fontes: BrazilSoyPanel.tsx, BrazilAlerts.tsx e BrazilMonitoringPanel.tsx. No modo demonstração, o Brasil não gera avaliações ou detecções reais. Para falta de dados: verificar sessão, integração, licença quando aplicável, limites do talhão, cobertura e quota. A configuração técnica deve ser revisada pelo responsável da organização.');
pair(s,['Antes de decidir','Confirme organização, talhão e coordenadas.\n\nAtualize o clima e as observações de campo.\n\nRevise as pendências com seu assessor e registre o relatório.'],['Quando faltarem dados','Confira a mensagem e tente atualizar.\n\nPara satélite, revise o contorno e a disponibilidade da fonte.\n\nSe o problema continuar, envie ao responsável a tela e o horário da consulta.']);

await fs.mkdir(path.join(dir,'renders'),{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(dir,'renders',`${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(dir,'candidate.pptx'));
await fs.writeFile(path.join(dir,'deck.json'),JSON.stringify(p.toProto()));
console.log('Built and rendered '+p.slides.items.length+' slides.');
