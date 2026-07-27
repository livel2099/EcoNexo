export type MisionesMunicipality = {
  name: string;
  department: string;
};

export type MisionesHub = MisionesMunicipality & {
  lat: number;
  lon: number;
};

export const MISIONES_TERRITORY_VERSION = "2026-07-27";
export const MISIONES_CENTER: [number, number] = [-26.92, -54.78];
export const POSADAS_CENTER: [number, number] = [-27.3621, -55.9007];
export const MISIONES_BOUNDS: [[number, number], [number, number]] = [
  [-28.20, -56.10],
  [-25.45, -53.55],
];

// Polígono operacional simplificado para validación local y encuadre de mapa.
// La API ofrece además /territory/resolve para normalización institucional.
export const MISIONES_POLYGON: [number, number][] = [
  [-25.50, -54.64], [-25.58, -54.30], [-25.62, -53.98],
  [-25.78, -53.72], [-26.05, -53.60], [-26.30, -53.57],
  [-26.62, -53.68], [-27.02, -53.88], [-27.36, -54.20],
  [-27.62, -54.64], [-27.93, -55.12], [-28.18, -55.66],
  [-27.84, -55.86], [-27.37, -55.96], [-27.06, -55.72],
  [-26.70, -55.42], [-26.35, -55.08], [-25.98, -54.82],
  [-25.66, -54.68], [-25.50, -54.64],
];

export const MISIONES_DEPARTMENTS = [
  "Apóstoles",
  "Cainguás",
  "Candelaria",
  "Capital",
  "Concepción",
  "Eldorado",
  "General Manuel Belgrano",
  "Guaraní",
  "Iguazú",
  "Leandro N. Alem",
  "Libertador General San Martín",
  "Montecarlo",
  "Oberá",
  "San Ignacio",
  "San Javier",
  "San Pedro",
  "25 de Mayo",
] as const;

// Nómina territorial de lanzamiento: 79 municipios, incluida Dos Hermanas.
export const MISIONES_MUNICIPALITIES: MisionesMunicipality[] = [
  { name: "Apóstoles", department: "Apóstoles" },
  { name: "Azara", department: "Apóstoles" },
  { name: "San José", department: "Apóstoles" },
  { name: "Tres Capones", department: "Apóstoles" },
  { name: "Aristóbulo del Valle", department: "Cainguás" },
  { name: "Campo Grande", department: "Cainguás" },
  { name: "Dos de Mayo", department: "Cainguás" },
  { name: "Salto Encantado", department: "Cainguás" },
  { name: "Bonpland", department: "Candelaria" },
  { name: "Candelaria", department: "Candelaria" },
  { name: "Cerro Corá", department: "Candelaria" },
  { name: "Loreto", department: "Candelaria" },
  { name: "Mártires", department: "Candelaria" },
  { name: "Profundidad", department: "Candelaria" },
  { name: "Santa Ana", department: "Candelaria" },
  { name: "Fachinal", department: "Capital" },
  { name: "Garupá", department: "Capital" },
  { name: "Posadas", department: "Capital" },
  { name: "Concepción de la Sierra", department: "Concepción" },
  { name: "Santa María", department: "Concepción" },
  { name: "9 de Julio", department: "Eldorado" },
  { name: "Colonia Delicia", department: "Eldorado" },
  { name: "Colonia Victoria", department: "Eldorado" },
  { name: "Eldorado", department: "Eldorado" },
  { name: "Santiago de Liniers", department: "Eldorado" },
  { name: "Bernardo de Irigoyen", department: "General Manuel Belgrano" },
  { name: "Comandante Andresito", department: "General Manuel Belgrano" },
  { name: "Dos Hermanas", department: "General Manuel Belgrano" },
  { name: "San Antonio", department: "General Manuel Belgrano" },
  { name: "El Soberbio", department: "Guaraní" },
  { name: "Fracrán", department: "Guaraní" },
  { name: "San Vicente", department: "Guaraní" },
  { name: "Puerto Esperanza", department: "Iguazú" },
  { name: "Puerto Iguazú", department: "Iguazú" },
  { name: "Puerto Libertad", department: "Iguazú" },
  { name: "Wanda", department: "Iguazú" },
  { name: "Almafuerte", department: "Leandro N. Alem" },
  { name: "Arroyo del Medio", department: "Leandro N. Alem" },
  { name: "Caá Yarí", department: "Leandro N. Alem" },
  { name: "Cerro Azul", department: "Leandro N. Alem" },
  { name: "Dos Arroyos", department: "Leandro N. Alem" },
  { name: "Gobernador López", department: "Leandro N. Alem" },
  { name: "Leandro N. Alem", department: "Leandro N. Alem" },
  { name: "Olegario Víctor Andrade", department: "Leandro N. Alem" },
  { name: "Capioví", department: "Libertador General San Martín" },
  { name: "El Alcázar", department: "Libertador General San Martín" },
  { name: "Garuhapé", department: "Libertador General San Martín" },
  { name: "Puerto Leoni", department: "Libertador General San Martín" },
  { name: "Puerto Rico", department: "Libertador General San Martín" },
  { name: "Ruiz de Montoya", department: "Libertador General San Martín" },
  { name: "Caraguatay", department: "Montecarlo" },
  { name: "Montecarlo", department: "Montecarlo" },
  { name: "Puerto Piray", department: "Montecarlo" },
  { name: "Campo Ramón", department: "Oberá" },
  { name: "Campo Viera", department: "Oberá" },
  { name: "Colonia Alberdi", department: "Oberá" },
  { name: "General Alvear", department: "Oberá" },
  { name: "Guaraní", department: "Oberá" },
  { name: "Los Helechos", department: "Oberá" },
  { name: "Oberá", department: "Oberá" },
  { name: "Panambí", department: "Oberá" },
  { name: "San Martín", department: "Oberá" },
  { name: "Colonia Polana", department: "San Ignacio" },
  { name: "Corpus Christi", department: "San Ignacio" },
  { name: "General Urquiza", department: "San Ignacio" },
  { name: "Gobernador Roca", department: "San Ignacio" },
  { name: "Hipólito Yrigoyen", department: "San Ignacio" },
  { name: "Jardín América", department: "San Ignacio" },
  { name: "San Ignacio", department: "San Ignacio" },
  { name: "Santo Pipó", department: "San Ignacio" },
  { name: "Florentino Ameghino", department: "San Javier" },
  { name: "Itacaruaré", department: "San Javier" },
  { name: "Mojón Grande", department: "San Javier" },
  { name: "San Javier", department: "San Javier" },
  { name: "Pozo Azul", department: "San Pedro" },
  { name: "San Pedro", department: "San Pedro" },
  { name: "25 de Mayo", department: "25 de Mayo" },
  { name: "Alba Posse", department: "25 de Mayo" },
  { name: "Colonia Aurora", department: "25 de Mayo" },
];

export const MISIONES_OPERATIONAL_HUBS: MisionesHub[] = [
  { name: "Posadas", department: "Capital", lat: -27.3621, lon: -55.9007 },
  { name: "Garupá", department: "Capital", lat: -27.4817, lon: -55.8292 },
  { name: "Candelaria", department: "Candelaria", lat: -27.4594, lon: -55.7456 },
  { name: "Santa Ana", department: "Candelaria", lat: -27.3696, lon: -55.5818 },
  { name: "San Ignacio", department: "San Ignacio", lat: -27.2559, lon: -55.5338 },
  { name: "Jardín América", department: "San Ignacio", lat: -27.0437, lon: -55.2265 },
  { name: "Puerto Rico", department: "Libertador General San Martín", lat: -26.8109, lon: -55.024 },
  { name: "Montecarlo", department: "Montecarlo", lat: -26.5662, lon: -54.7574 },
  { name: "Eldorado", department: "Eldorado", lat: -26.4087, lon: -54.6946 },
  { name: "Puerto Iguazú", department: "Iguazú", lat: -25.5972, lon: -54.5786 },
  { name: "Comandante Andresito", department: "General Manuel Belgrano", lat: -25.6694, lon: -54.0451 },
  { name: "Bernardo de Irigoyen", department: "General Manuel Belgrano", lat: -26.2552, lon: -53.6478 },
  { name: "San Antonio", department: "General Manuel Belgrano", lat: -26.01709, lon: -53.78987 },
  { name: "San Pedro", department: "San Pedro", lat: -26.6221, lon: -54.1084 },
  { name: "El Soberbio", department: "Guaraní", lat: -27.2967, lon: -54.1988 },
  { name: "Oberá", department: "Oberá", lat: -27.4871, lon: -55.1199 },
  { name: "Leandro N. Alem", department: "Leandro N. Alem", lat: -27.6034, lon: -55.3249 },
  { name: "Apóstoles", department: "Apóstoles", lat: -27.9143, lon: -55.7541 },
  { name: "San Javier", department: "San Javier", lat: -27.8743, lon: -55.1351 },
  { name: "25 de Mayo", department: "25 de Mayo", lat: -27.3768, lon: -54.7431 },
  { name: "Aristóbulo del Valle", department: "Cainguás", lat: -27.0967, lon: -54.8963 },
  { name: "Concepción de la Sierra", department: "Concepción", lat: -27.9831, lon: -55.5203 },
  { name: "San Vicente", department: "Guaraní", lat: -26.9955, lon: -54.4872 },
  { name: "Wanda", department: "Iguazú", lat: -25.9713, lon: -54.5731 },
  { name: "Dos Hermanas", department: "General Manuel Belgrano", lat: -26.278, lon: -53.757 },
];

export function municipalityDepartment(name: string): string | null {
  return MISIONES_MUNICIPALITIES.find((item) => item.name === name)?.department || null;
}

export function isInMisiones(lat: number, lon: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
  const [[south, west], [north, east]] = MISIONES_BOUNDS;
  if (lat < south || lat > north || lon < west || lon > east) return false;
  let inside = false;
  for (let i = 0, j = MISIONES_POLYGON.length - 1; i < MISIONES_POLYGON.length; j = i++) {
    const [latI, lonI] = MISIONES_POLYGON[i];
    const [latJ, lonJ] = MISIONES_POLYGON[j];
    const intersects = ((lonI > lon) !== (lonJ > lon))
      && (lat < ((latJ - latI) * (lon - lonI)) / ((lonJ - lonI) || Number.EPSILON) + latI);
    if (intersects) inside = !inside;
  }
  return inside;
}

function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRad = (value: number) => value * Math.PI / 180;
  const radius = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * radius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function nearestMisionesHub(lat: number, lon: number): MisionesHub {
  return MISIONES_OPERATIONAL_HUBS.reduce((nearest, hub) => (
    distanceKm(lat, lon, hub.lat, hub.lon) < distanceKm(lat, lon, nearest.lat, nearest.lon) ? hub : nearest
  ), MISIONES_OPERATIONAL_HUBS[0]);
}

export function misionesLocationLabel(lat: number, lon: number): string {
  if (!isInMisiones(lat, lon)) return "Fuera del territorio operativo de Misiones";
  const hub = nearestMisionesHub(lat, lon);
  return `${hub.name} · Dpto. ${hub.department} · Misiones`;
}

export function assertMisionesCoordinates(lat: number, lon: number): void {
  if (!isInMisiones(lat, lon)) throw new Error("La ubicación debe estar dentro de la provincia de Misiones.");
}
