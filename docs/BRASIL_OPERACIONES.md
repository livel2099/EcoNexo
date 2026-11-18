# Brasil: operação de laranja e eucalipto em Mato Grosso

Implementação local para uma carteira de referência de 450.000 ha. A área efetivamente monitorada vem dos polígonos importados; o número de referência não representa cobertura contratada ou validada. Interface em português e espanhol.

## Ativação

1. Aplicar `apps/api/migrations/30_brazil_operations.sql` pelo processo de migração existente, após validar em PostgreSQL/PostGIS de homologação. Requer as migrações anteriores de organizações, usuários e assinaturas. A migração não foi aplicada em produção nesta entrega.
2. Importar os limites reais em GeoJSON WGS84, em lotes de até 200 feições. Cada Feature deve conter `properties.code`, `name`, `estate` e `crop` (`orange`, `eucalyptus`, `soy` ou `reserve`). `cultivar`, `manager` e `planted_on` são opcionais. Geometrias Polygon/MultiPolygon devem estar dentro de Mato Grosso, ser válidas e não se sobrepor. A importação é atômica e rejeita códigos já cadastrados.
3. Configurar os serviços no servidor, nunca no navegador:
   - `NASA_FIRMS_KEY` e `FIRMS_INLINE_ENABLED=true`: focos VIIRS NOAA-20/NOAA-21.
   - `COPERNICUS_CLIENT_ID` e `COPERNICUS_CLIENT_SECRET`: consultas de vegetação.
   - `BRAZIL_SMTP_HOST`, `BRAZIL_SMTP_PORT=587`, `BRAZIL_SMTP_USER`, `BRAZIL_SMTP_PASSWORD`, `BRAZIL_MAIL_FROM`: e-mail com STARTTLS.
   - `BRAZIL_WHATSAPP_TOKEN`, `BRAZIL_WHATSAPP_PHONE_ID`, `BRAZIL_WHATSAPP_TEMPLATE`, `BRAZIL_WHATSAPP_VERSION`: WhatsApp Cloud API. A versão deve ser compatível com a conta. O template aprovado deve usar idioma `pt_BR` e um parâmetro de texto no corpo.
   - `BRAZIL_OPERATIONS_ENABLED=true`: trabalhadores periódicos. Usar pool de banco com capacidade acima das três conexões reservadas para locks e das consultas concorrentes (padrão 10).
4. Em Configuração, o administrador cadastra destinatários, consentimento, raio de proximidade e ativa o monitoramento da organização. O cadastro não envia mensagem de teste. Só organizações ativas, aprovadas e com assinatura válida entram nos trabalhadores.
5. Validar em homologação um foco dentro/fora do raio, isolamento entre organizações, consulta de temperatura, inspeção e entrega a destinatários de teste autorizados. Conferir o painel de entregas e os logs antes da ativação operacional.

## O que os dados significam

- Incêndios: pontos de calor das últimas 48 horas, cruzados com os polígonos e raio configurado. São indícios a verificar, não confirmação de incêndio. A disponibilidade depende da passagem dos satélites e do provedor. Falhas e cobertura parcial ficam explícitas. Observações de satélites diferentes podem corresponder ao mesmo incidente; não tratar a quantidade de alertas como quantidade de incêndios.
- Sanidade: inspeções, amostragem e capturas em armadilhas para laranja e eucalipto. A incidência vale para a amostra. Confirmação exige profissional e referência diagnóstica. Não há reconhecimento automático de espécie de praga por imagem.
- Vegetação: triagem de queda absoluta de NDVI de pelo menos 0,15 contra as três observações anteriores, com quatro datas válidas, cobertura de pixels de pelo menos 70% e observação recente. É uma regra de triagem não calibrada por cultivar, idade ou estação; exige vistoria e pode refletir colheita, seca ou manejo. Polígonos fora dos limites do conector precisam de subdivisão, indicada no painel.
- Temperatura: consulta automática do modelo meteorológico ao abrir um talhão sem contexto recente; trabalhadores atualizam os cadastrados em lotes. A estimativa de solo a 6 cm é identificada como modelo com data e fonte. Uma leitura recente de sensor tem preferência quando disponível.
- pH: sem sensores instalados não existe medição automática de pH nesta entrega. O painel aceita resultado de laboratório com método, profundidade, data e referência. A API de telemetria está preparada para sensores futuros, com autenticação interna e calibração recente. Não há valor fictício ou estimativa cartográfica apresentada como medição. A consulta exploratória ao SoilGrids não forneceu valores utilizáveis e não foi integrada.

## Operação e limites

O painel mantém alertas, responsáveis, decisões e trilha de ações. E-mail e WhatsApp usam fila persistente com deduplicação por alerta/canal/destinatário. `accepted` significa aceitação pelo provedor, não leitura nem entrega confirmada. Em falha ambígua, o envio fica `uncertain` para investigação e não é repetido automaticamente. Destinatários removidos ou sem consentimento são cancelados antes do envio.

Os trabalhadores são independentes: incêndios aguardam 300 segundos entre ciclos; contexto e satélite, 60; entregas, 30. Cada ciclo processa no máximo 50 organizações para focos, 12 talhões para contexto, 3 para satélite e 20 entregas. A duração das chamadas soma-se ao intervalo. São limites conservadores, não SLA. Existem paginação, índices espaciais e locks entre réplicas; a capacidade para toda a carteira ainda precisa de teste de carga com o número real de talhões e cotas dos provedores. Não houve validação operacional de 450.000 ha.

## Verificação desta entrega

43 testes de API/regras passaram, incluindo permissões, escopo por organização, validação de amostras, deduplicação e cancelamento de destinatários. TypeScript passou. Os testes de banco usam doubles; falta executar integração real PostGIS e entrega real dos provedores. O Docker local não estava disponível. Nenhuma credencial foi criada e nenhuma mensagem real foi enviada.

## Referências

- [NASA FIRMS: API de área](https://firms.modaps.eosdis.nasa.gov/api/area/).
- [Fundecitrus: greening e psilídeo](https://www.fundecitrus.com.br/pragas-e-doencas/greening-e-psilideo/).
- [Embrapa: sanidade florestal](https://www.atermaisdigital.cnptia.embrapa.br/web/ilpf/floresta).
- [ISRIC: SoilGrids](https://isric.org/explore/soilgrids/).
