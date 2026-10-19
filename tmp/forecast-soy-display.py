from pathlib import Path
p=Path('apps/web/components/ParaguaySoyPanel.tsx');s=p.read_text(encoding='utf-8')
s=s.replace('<AutomaticData data={automatic}/>', '<><AutomaticData data={automatic}/><ForecastData rows={automatic?.forecast||[]} error={automatic?.error}/></>')
a=s.index('<h4>Próximos 7 días</h4>');b=s.index('<h4>Recomendaciones para la plantación</h4>',a)
s=s[:a]+'<ForecastData rows={report.forecast} error={report.weather_error}/>'+s[b:]
s=s.replace("report.forecast.map(d=>`<tr>${[d.day,d.tmax,d.tmin,d.precipitation_mm,d.et0_mm].map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')", "report.forecast.length?report.forecast.map(d=>`<tr>${[d.day,d.tmax,d.tmin,d.precipitation_mm,d.et0_mm].map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join(''):'<tr><td colspan=\"5\">Sin pronóstico disponible. Reintentar la consulta automática.</td></tr>'")
p.write_text(s,encoding='utf-8')
