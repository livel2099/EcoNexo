"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { translateBrazil, type BrazilLanguage } from '../app/lib/brazil-translations';

const STORAGE_KEY = 'econexo.brazil.language';
const BrazilLanguageContext = createContext<BrazilLanguage>('es');

export function useBrazilLanguage() {
  const language = useContext(BrazilLanguageContext);
  const t = useCallback((text: string) => translateBrazil(text, language), [language]);
  return { language, locale: language === 'pt' ? 'pt-BR' : 'es-AR', t };
}

export function BrazilLanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<BrazilLanguage>('es');
  useEffect(() => {
    try { if (localStorage.getItem(STORAGE_KEY) === 'pt') setLanguage('pt'); } catch { /* Storage may be disabled. */ }
  }, []);
  function selectLanguage(value: BrazilLanguage) {
    setLanguage(value);
    try { localStorage.setItem(STORAGE_KEY, value); } catch { /* The selection still works for this visit. */ }
  }
  return <BrazilLanguageContext.Provider value={language}>
    <div lang={language === 'pt' ? 'pt-BR' : 'es'}>
      <div className="workspace-map-tools" role="group" aria-label={language === 'pt' ? 'Idioma da seção Brasil' : 'Idioma de la sección Brasil'}>
        <span>Idioma</span>
        <button type="button" lang="es" aria-pressed={language === 'es'} className={language === 'es' ? 'active' : ''} onClick={() => selectLanguage('es')}>Español</button>
        <button type="button" lang="pt-BR" aria-pressed={language === 'pt'} className={language === 'pt' ? 'active' : ''} onClick={() => selectLanguage('pt')}>Português</button>
      </div>
      {children}
    </div>
  </BrazilLanguageContext.Provider>;
}
