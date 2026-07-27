import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert as NativeAlert,
  Image,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  Share,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import * as AuthSession from "expo-auth-session";
import * as Google from "expo-auth-session/providers/google";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import { StatusBar } from "expo-status-bar";
import * as WebBrowser from "expo-web-browser";
import MapView, { Marker } from "react-native-maps";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";

import {
  API_URL,
  DEMO_MODE,
  actOnAlert,
  apiHealth,
  authenticateGoogle,
  clearSession,
  getDashboardBundle,
  loadSession,
  login,
  register,
  registerAlertShare,
  saveSession,
  submitInternalReport,
  type AlertShareInput,
  type MobileReportInput,
} from "./src/api";
import {
  buildFireReading,
  fetchEarthNow,
  firePublicMessage,
  relativeTime,
} from "./src/environment";
import { colors, radii, spacing } from "./src/theme";
import { MISIONES_CENTER, MISIONES_MUNICIPALITIES, isInMisiones, municipalityDepartment } from "./src/territory";
import type {
  Alert,
  DashboardBundle,
  EarthNow,
  EnvironmentalIndex,
  ModuleEntitlement,
  Session,
} from "./src/types";

WebBrowser.maybeCompleteAuthSession();

const BRAND = require("./assets/brand-lockup.jpg") as number;

type AppTab = "inicio" | "fuego" | "ia" | "reportar" | "cuenta";
type AuthMode = "login" | "register";
type Vertical = "municipio" | "forestal" | "energetica";
type ReportType = MobileReportInput["type"];
type Audience = AlertShareInput["audience"];

const DEFAULT_CENTER = MISIONES_CENTER;
const GOOGLE_WEB_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || "";
const GOOGLE_ANDROID_ID = process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID || "";
const GOOGLE_IOS_ID = process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID || "";
const GOOGLE_FALLBACK_ID = "google-oauth-disabled.apps.googleusercontent.com";

function short(value: number | null | undefined, digits = 0): string {
  return value == null || !Number.isFinite(value) ? "s/d" : value.toFixed(digits);
}

function levelColor(level: string): string {
  const normalized = level.toLowerCase();
  if (["r5", "critica", "critico", "emergencia"].includes(normalized)) return colors.red;
  if (["r4", "alta"].includes(normalized)) return colors.orange;
  if (["r3", "media", "atencion"].includes(normalized)) return colors.yellow;
  if (["r2"].includes(normalized)) return colors.blue;
  return colors.green;
}

function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function AppButton({
  children,
  onPress,
  disabled = false,
  variant = "primary",
}: {
  children: React.ReactNode;
  onPress: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger" | "whatsapp" | "telegram";
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        variant === "secondary" && styles.buttonSecondary,
        variant === "danger" && styles.buttonDanger,
        variant === "whatsapp" && styles.buttonWhatsApp,
        variant === "telegram" && styles.buttonTelegram,
        disabled && styles.buttonDisabled,
        pressed && !disabled && styles.buttonPressed,
      ]}
    >
      <Text style={[styles.buttonText, variant === "secondary" && styles.buttonTextSecondary]}>{children}</Text>
    </Pressable>
  );
}

function Field({
  label,
  value,
  onChangeText,
  placeholder,
  secureTextEntry = false,
  keyboardType = "default",
  multiline = false,
  autoCapitalize = "sentences",
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder: string;
  secureTextEntry?: boolean;
  keyboardType?: "default" | "email-address" | "numeric" | "decimal-pad";
  multiline?: boolean;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
}) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        keyboardType={keyboardType}
        multiline={multiline}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        secureTextEntry={secureTextEntry}
        style={[styles.input, multiline && styles.textarea]}
        value={value}
      />
    </View>
  );
}

function SectionHeader({ eyebrow, title, description }: { eyebrow?: string; title: string; description?: string }) {
  return (
    <View style={styles.sectionHeader}>
      {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
      <Text style={styles.sectionTitle}>{title}</Text>
      {description ? <Text style={styles.sectionDescription}>{description}</Text> : null}
    </View>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <View style={styles.emptyCard}>
      <Text style={styles.emptyIcon}>◎</Text>
      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.muted}>{text}</Text>
    </View>
  );
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (session: Session) => Promise<void> }) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [organization, setOrganization] = useState("EcoNexo");
  const [vertical, setVertical] = useState<Vertical>("forestal");
  const [municipality, setMunicipality] = useState("Posadas");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [message, setMessage] = useState("");

  const platformGoogleId = Platform.select({
    ios: GOOGLE_IOS_ID,
    android: GOOGLE_ANDROID_ID,
    default: GOOGLE_WEB_ID,
  }) || GOOGLE_WEB_ID;
  const googleEnabled = Boolean(platformGoogleId || GOOGLE_WEB_ID);
  const [googleRequest, googleResponse, promptGoogle] = Google.useAuthRequest({
    webClientId: GOOGLE_WEB_ID || GOOGLE_FALLBACK_ID,
    androidClientId: GOOGLE_ANDROID_ID || GOOGLE_WEB_ID || GOOGLE_FALLBACK_ID,
    iosClientId: GOOGLE_IOS_ID || GOOGLE_WEB_ID || GOOGLE_FALLBACK_ID,
    clientId: platformGoogleId || GOOGLE_FALLBACK_ID,
    responseType: AuthSession.ResponseType.IdToken,
    scopes: ["openid", "profile", "email"],
  });

  useEffect(() => {
    void apiHealth().then(setApiOnline);
  }, []);

  useEffect(() => {
    if (googleResponse?.type !== "success") return;
    const authentication = googleResponse.authentication as { idToken?: string } | null;
    const credential = googleResponse.params?.id_token || authentication?.idToken;
    if (!credential) {
      setMessage("Google no devolvió un ID token. Revisá los client IDs configurados para la app.");
      return;
    }
    setBusy(true);
    setMessage("");
    void authenticateGoogle({
      credential,
      mode,
      organization_name: mode === "register" ? organization : undefined,
      vertical: mode === "register" ? vertical : undefined,
      municipality: mode === "register" ? municipality : undefined,
      department: mode === "register" ? municipalityDepartment(municipality) || "Capital" : undefined,
      terms_accepted: mode === "register" ? terms : undefined,
      legal_version: "2026-07-27",
    })
      .then(onAuthenticated)
      .catch((cause: unknown) => setMessage(cause instanceof Error ? cause.message : "No se pudo ingresar con Google."))
      .finally(() => setBusy(false));
  }, [googleResponse, mode, municipality, onAuthenticated, organization, terms, vertical]);

  async function submit() {
    setMessage("");
    if (mode === "register") {
      if (!name.trim() || !organization.trim()) return setMessage("Completá la organización y el nombre del administrador.");
      if (password !== repeatPassword) return setMessage("Las contraseñas no coinciden.");
      if (!terms) return setMessage("Debés aceptar los Términos y la Política de Privacidad.");
    }
    setBusy(true);
    try {
      const session = mode === "login"
        ? await login(email, password)
        : await register({
          organization_name: organization,
          vertical,
          municipality,
          department: municipalityDepartment(municipality) || "Capital",
          name,
          email,
          password,
          terms_accepted: terms,
          legal_version: "2026-07-27",
        });
      await onAuthenticated(session);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "No se pudo completar el acceso.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.authSafe}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.authScroll} keyboardShouldPersistTaps="handled">
          <View style={styles.authCard}>
            <Image accessibilityLabel="EcoNexo Earth Intelligence" resizeMode="contain" source={BRAND} style={styles.authLogo} />
            <View style={[styles.connectionPill, apiOnline === false && styles.connectionPillError]}>
              <View style={[styles.connectionDot, apiOnline === false && styles.connectionDotError]} />
              <Text style={styles.connectionText}>
                {DEMO_MODE ? "Demo autónoma activa" : apiOnline == null ? "Comprobando API…" : apiOnline ? "API y base conectadas" : "API sin conexión"}
              </Text>
            </View>

            <View style={styles.segmented}>
              <Pressable onPress={() => setMode("login")} style={[styles.segment, mode === "login" && styles.segmentActive]}>
                <Text style={[styles.segmentText, mode === "login" && styles.segmentTextActive]}>Ingresar</Text>
              </Pressable>
              <Pressable onPress={() => setMode("register")} style={[styles.segment, mode === "register" && styles.segmentActive]}>
                <Text style={[styles.segmentText, mode === "register" && styles.segmentTextActive]}>Crear organización</Text>
              </Pressable>
            </View>

            <SectionHeader
              eyebrow="ACCESO SEGURO"
              title={mode === "login" ? "Entrá al centro de comando" : "Activá tu espacio institucional"}
              description={mode === "login"
                ? "Accedé a alertas, reportes, dispositivos y módulos licenciados."
                : "El primer usuario quedará registrado como administrador. Google es opcional."}
            />

            {mode === "register" ? (
              <>
                <Field label="Nombre de la organización" onChangeText={setOrganization} placeholder="Municipalidad, empresa o laboratorio" value={organization} />
                <Field label="Municipio base de Misiones" onChangeText={setMunicipality} placeholder="Ej.: Posadas" value={municipality} />
                <Text style={styles.helperText}>Usá una de las {MISIONES_MUNICIPALITIES.length} localidades habilitadas. Departamento: {municipalityDepartment(municipality) || "verificá el nombre"}.</Text>
                <Text style={styles.label}>Tipo de operación</Text>
                <View style={styles.choiceRow}>
                  {(["municipio", "forestal", "energetica"] as Vertical[]).map((item) => (
                    <Pressable key={item} onPress={() => setVertical(item)} style={[styles.choice, vertical === item && styles.choiceActive]}>
                      <Text style={[styles.choiceText, vertical === item && styles.choiceTextActive]}>{item === "energetica" ? "Energía" : titleCase(item)}</Text>
                    </Pressable>
                  ))}
                </View>
                <Field label="Nombre y apellido del administrador" onChangeText={setName} placeholder="Nombre completo" value={name} />
              </>
            ) : null}

            <Field autoCapitalize="none" keyboardType="email-address" label="Email" onChangeText={setEmail} placeholder="tu@organizacion.org" value={email} />
            <Field autoCapitalize="none" label="Contraseña" onChangeText={setPassword} placeholder="Mínimo 8 caracteres" secureTextEntry value={password} />
            {mode === "register" ? (
              <Field autoCapitalize="none" label="Repetir contraseña" onChangeText={setRepeatPassword} placeholder="Repetí la contraseña" secureTextEntry value={repeatPassword} />
            ) : null}

            {mode === "register" ? (
              <Pressable onPress={() => setTerms((value) => !value)} style={styles.termsRow}>
                <Switch onValueChange={setTerms} thumbColor={terms ? colors.green : colors.muted} trackColor={{ false: colors.border, true: colors.borderBright }} value={terms} />
                <Text style={styles.termsText}>Acepto los Términos y Condiciones y la Política de Privacidad.</Text>
              </Pressable>
            ) : null}

            <AppButton disabled={busy || !email || !password} onPress={() => void submit()}>
              {busy ? "Procesando…" : mode === "login" ? "Ingresar" : "Crear organización y entrar"}
            </AppButton>

            <View style={styles.dividerRow}><View style={styles.divider} /><Text style={styles.dividerText}>O CONTINUAR CON</Text><View style={styles.divider} /></View>
            <AppButton
              disabled={busy || !googleEnabled || !googleRequest || (mode === "register" && !terms)}
              onPress={() => void promptGoogle()}
              variant="secondary"
            >
              {googleEnabled ? "G  Continuar con Google" : "Google OAuth no configurado"}
            </AppButton>
            <Text style={styles.helperText}>
              {googleEnabled
                ? "Google devuelve una credencial al backend; EcoNexo no recibe tu contraseña de Google."
                : "El registro por email sigue disponible. Para Google, cargá los client IDs de Android, iOS o web en apps/mobile/.env."}
            </Text>

            {message ? <View style={styles.errorBox}><Text style={styles.errorText}>{message}</Text></View> : null}
            <Text style={styles.apiText}>API configurada: {API_URL}</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function HomeScreen({ bundle, earth, onSelectAlert, refreshing, onRefresh }: {
  bundle: DashboardBundle;
  earth: EarthNow | null;
  onSelectAlert: (alert: Alert) => void;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const online = bundle.devices.filter((device) => device.status === "online").length;
  const activeAlerts = bundle.alerts.filter((alert) => !["resuelta", "descartada"].includes(alert.status));
  return (
    <ScrollView contentContainerStyle={styles.screenContent} refreshControl={<RefreshControl onRefresh={onRefresh} refreshing={refreshing} tintColor={colors.cyan} />}>
      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>EARTH INTELLIGENCE · OPERACIÓN MÓVIL</Text>
        <Text style={styles.heroTitle}>{bundle.org.name}</Text>
        <Text style={styles.heroText}>Una vista ejecutiva para decidir rápido, verificar señales y comunicar con responsabilidad.</Text>
        <View style={styles.heroStatusRow}>
          <View style={[styles.statusOrb, { borderColor: levelColor(bundle.kpi.global_status) }]}><Text style={styles.statusOrbValue}>{activeAlerts.length}</Text><Text style={styles.statusOrbLabel}>alertas</Text></View>
          <View style={styles.heroStatusCopy}><Text style={styles.heroStatusTitle}>{bundle.kpi.global_status === "normal" ? "Operación estable" : "Requiere atención"}</Text><Text style={styles.muted}>{online} de {bundle.devices.length} nodos conectados · última consulta {earth ? relativeTime(earth.fetchedAt) : "sin dato"}</Text></View>
        </View>
      </View>

      <View style={styles.kpiGrid}>
        <KpiCard label="Detección" value={bundle.kpi.detection_time_s == null ? "s/d" : `${Math.round(bundle.kpi.detection_time_s)} s`} detail={`meta < ${bundle.kpi.detection_target_s} s`} />
        <KpiCard label="Precisión" value={bundle.kpi.model_precision == null ? "s/d" : `${Math.round(bundle.kpi.model_precision * 100)}%`} detail={`meta ${Math.round(bundle.kpi.precision_target * 100)}%`} />
        <KpiCard label="Reportes válidos" value={bundle.kpi.valid_reports_rate == null ? "s/d" : `${Math.round(bundle.kpi.valid_reports_rate * 100)}%`} detail={`${bundle.reports.length} reportes`} />
        <KpiCard label="Respuesta" value={bundle.kpi.response_time_reduction == null ? "s/d" : `-${Math.round(bundle.kpi.response_time_reduction * 100)}%`} detail="reducción estimada" />
      </View>

      <SectionHeader eyebrow="PRIORIDAD OPERATIVA" title="Alertas activas" description="Tocá una alerta para confirmarla, escalarla o descartarla." />
      {activeAlerts.length ? activeAlerts.slice(0, 5).map((alert) => (
        <Pressable key={alert.id} onPress={() => onSelectAlert(alert)} style={styles.alertCard}>
          <View style={[styles.severityLine, { backgroundColor: levelColor(alert.severity) }]} />
          <View style={styles.alertBody}>
            <View style={styles.cardTopRow}><Text style={styles.cardTitle}>{alert.title}</Text><Text style={[styles.badge, { color: levelColor(alert.severity), borderColor: levelColor(alert.severity) }]}>{alert.severity.toUpperCase()}</Text></View>
            <Text style={styles.muted}>{titleCase(alert.type)} · {relativeTime(alert.detected_at)} · confianza {Math.round(alert.confidence * 100)}%</Text>
            <Text style={styles.coordinates}>{alert.lat.toFixed(4)}, {alert.lon.toFixed(4)}</Text>
          </View>
        </Pressable>
      )) : <EmptyState title="Sin alertas activas" text="La red no registra incidentes pendientes en este momento." />}

      <SectionHeader eyebrow="RED DE CAMPO" title="Dispositivos" description="Estado básico de la red IoT conectada." />
      {localDevices.map((device) => (
        <View key={device.id} style={styles.deviceCard}>
          <View style={[styles.deviceDot, device.status === "online" ? styles.deviceOnline : styles.deviceOffline]} />
          <View style={styles.deviceText}><Text style={styles.cardTitle}>{device.name}</Text><Text style={styles.muted}>{device.external_id} · {device.tags.join(" · ") || "sin etiquetas"}</Text></View>
          <View><Text style={styles.deviceBattery}>{device.battery == null ? "s/d" : `${Math.round(device.battery)}%`}</Text><Text style={styles.deviceLastSeen}>{device.last_seen ? relativeTime(device.last_seen) : "sin señal"}</Text></View>
        </View>
      ))}
    </ScrollView>
  );
}

function KpiCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <View style={styles.kpiCard}><Text style={styles.kpiLabel}>{label}</Text><Text style={styles.kpiValue}>{value}</Text><Text style={styles.kpiDetail}>{detail}</Text></View>;
}

function FireScreen({ session, bundle, earth, center, refreshing, onRefresh }: {
  session: Session;
  bundle: DashboardBundle;
  earth: EarthNow | null;
  center: { latitude: number; longitude: number };
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const [audience, setAudience] = useState<Audience>("organizacion");
  const [sharing, setSharing] = useState(false);
  const entitlement = bundle.modules.find((module) => module.module_key === "fire_smoke") || null;
  const fireAlerts = bundle.alerts.filter((alert) => isInMisiones(alert.lat, alert.lon) && ["incendio", "calidad_aire"].includes(alert.type));
  const localDevices = bundle.devices.filter((item) => isInMisiones(item.lat, item.lon));
  const localDetections = bundle.detections.filter((item) => isInMisiones(item.lat, item.lon));
  const reading = useMemo(() => buildFireReading(
    center.latitude,
    center.longitude,
    localDetections,
    earth,
    fireAlerts.some((alert) => alert.severity === "critica"),
  ), [bundle.detections, center.latitude, center.longitude, earth, fireAlerts]);
  const message = useMemo(() => firePublicMessage(center.latitude, center.longitude, reading, earth), [center.latitude, center.longitude, earth, reading]);

  async function shareChannel(channel: "whatsapp" | "telegram" | "otro") {
    setSharing(true);
    try {
      await registerAlertShare(session, {
        channel,
        audience,
        title: reading.headline,
        message,
        module_key: "fire_smoke",
        metadata: {
          latitude: center.latitude,
          longitude: center.longitude,
          detections_48h: reading.detections48h,
          pm25: earth?.pm25,
          aqi: earth?.usAqi,
        },
      });
      if (channel === "otro") {
        await Share.share({ message, title: "EcoNexo · Focos de incendio y humo" });
      } else {
        const encoded = encodeURIComponent(message);
        const url = channel === "whatsapp"
          ? `https://wa.me/?text=${encoded}`
          : `https://t.me/share/url?url=${encodeURIComponent("https://econexo.app")}&text=${encoded}`;
        await Linking.openURL(url);
      }
    } catch (cause) {
      NativeAlert.alert("No se pudo compartir", cause instanceof Error ? cause.message : "Revisá la conexión.");
    } finally {
      setSharing(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.screenContent} refreshControl={<RefreshControl onRefresh={onRefresh} refreshing={refreshing} tintColor={colors.cyan} />}>
      <View style={styles.moduleHeader}>
        <View style={styles.moduleHeaderText}>
          <Text style={styles.eyebrow}>MÓDULO LICENCIADO · LENGUAJE CLARO</Text>
          <Text style={styles.heroTitle}>Focos de incendio forestal y humo</Text>
          <Text style={styles.heroText}>Primero explica qué pasa; después muestra los datos. Pensado para municipios, brigadas, medios, organizaciones y laboratorios.</Text>
        </View>
        <LicensePill entitlement={entitlement} />
      </View>

      <View style={[styles.publicStatus, { borderColor: levelColor(reading.level) }]}>
        <View style={[styles.publicStatusIcon, { borderColor: levelColor(reading.level) }]}><Text style={[styles.publicStatusIconText, { color: levelColor(reading.level) }]}>{reading.level === "normal" ? "✓" : "!"}</Text></View>
        <View style={styles.publicStatusText}><Text style={styles.eyebrow}>LECTURA PARA TODO PÚBLICO</Text><Text style={styles.publicHeadline}>{reading.headline}</Text><Text style={styles.bodyText}>{reading.explanation}</Text></View>
      </View>

      <View style={styles.quickGrid}>
        <MiniFact icon="🛰️" value={String(reading.detections48h)} label="puntos calientes / 48 h" />
        <MiniFact icon="🌫️" value={short(earth?.pm25, 1)} label="PM2.5 µg/m³" />
        <MiniFact icon="💨" value={short(earth?.windSpeed)} label="viento km/h" />
      </View>

      <SectionHeader eyebrow="MAPA DE VERIFICACIÓN" title="¿Dónde está pasando?" description="Naranja: señal térmica satelital. Rojo: alerta. Verde: nodo IoT. Una señal térmica necesita verificación." />
      <View style={styles.mapFrame}>
        <MapView
          initialRegion={{ ...center, latitudeDelta: 0.55, longitudeDelta: 0.55 }}
          region={{ ...center, latitudeDelta: 0.55, longitudeDelta: 0.55 }}
          style={styles.map}
        >
          {localDevices.map((device) => <Marker coordinate={{ latitude: device.lat, longitude: device.lon }} description={device.external_id} key={device.id} pinColor={colors.green} title={device.name} />)}
          {localDetections.map((detection) => <Marker coordinate={{ latitude: detection.lat, longitude: detection.lon }} description={`${detection.source} · ${relativeTime(detection.acquired_at)}`} key={detection.id} pinColor={colors.orange} title="Punto caliente a verificar" />)}
          {fireAlerts.map((alert) => <Marker coordinate={{ latitude: alert.lat, longitude: alert.lon }} description={`${alert.severity} · ${relativeTime(alert.detected_at)}`} key={alert.id} pinColor={colors.red} title={alert.title} />)}
        </MapView>
        <View style={styles.mapLegend}><Text style={styles.mapLegendText}>● nodo</Text><Text style={[styles.mapLegendText, { color: colors.orange }]}>● satélite</Text><Text style={[styles.mapLegendText, { color: colors.red }]}>● alerta</Text></View>
      </View>

      <SectionHeader eyebrow="QUÉ SIGNIFICA" title="Sin tecnicismos innecesarios" />
      <PlainFact icon="🛰️" title="Punto caliente" text={reading.nearest ? `El más cercano está a ${reading.nearest.distance.toFixed(1)} km. Puede ser incendio, quema controlada u otra fuente de calor.` : "No hay señales térmicas cercanas cargadas en las últimas 48 horas."} />
      <PlainFact icon="🌫️" title="Humo y aire" text={(earth?.pm25 ?? 0) >= 35 || (earth?.usAqi ?? 0) >= 151 ? "El aire muestra partículas elevadas. Niños, mayores y personas con asma o EPOC deberían reducir exposición y seguir indicaciones oficiales." : "No se observa un deterioro fuerte del aire en el dato disponible."} />
      <PlainFact icon="💨" title="Propagación" text={reading.dry && reading.highWind ? "Hay sequedad y ráfagas fuertes: un foco podría avanzar rápidamente." : reading.dry ? "El suelo aparece seco, aunque el viento no es extremo." : "Las condiciones actuales no muestran una combinación fuerte de sequedad y viento."} />
      <PlainFact icon="📞" title="Qué hacer" text="Si ves fuego o una columna de humo, alejate, no bloquees caminos y llamá al 911 con una referencia clara del lugar." />

      <View style={styles.shareCard}>
        <SectionHeader eyebrow="APROBACIÓN HUMANA" title="Preparar alerta para WhatsApp o Telegram" description="EcoNexo genera un borrador y registra el canal, pero no publica automáticamente." />
        <Text style={styles.label}>Destinatario</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalChoices}>
          {(["organizacion", "medios", "laboratorio", "emergencia", "publico"] as Audience[]).map((item) => (
            <Pressable key={item} onPress={() => setAudience(item)} style={[styles.choice, audience === item && styles.choiceActive]}>
              <Text style={[styles.choiceText, audience === item && styles.choiceTextActive]}>{titleCase(item)}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <View style={styles.messagePreview}><Text selectable style={styles.messageText}>{message}</Text></View>
        <View style={styles.shareButtons}>
          <AppButton disabled={sharing || entitlement?.available === false} onPress={() => void shareChannel("whatsapp")} variant="whatsapp">WhatsApp</AppButton>
          <AppButton disabled={sharing || entitlement?.available === false} onPress={() => void shareChannel("telegram")} variant="telegram">Telegram</AppButton>
          <AppButton disabled={sharing || entitlement?.available === false} onPress={() => void shareChannel("otro")} variant="secondary">Más opciones</AppButton>
        </View>
      </View>

      <View style={styles.legalCard}>
        <Text style={styles.eyebrow}>CRITERIO OPERATIVO</Text>
        <Text style={styles.cardTitle}>Alerta temprana, monitoreo diferencial y verificación</Text>
        <Text style={styles.bodyText}>El módulo integra satélite, sensores, cámaras y reportes cuando están disponibles. No se presenta como sistema oficial ni reemplaza a Ecología, Manejo del Fuego, Policía, Bomberos o 911.</Text>
      </View>
    </ScrollView>
  );
}

function LicensePill({ entitlement }: { entitlement: ModuleEntitlement | null }) {
  const active = entitlement?.available !== false;
  return (
    <View style={[styles.licensePill, !active && styles.licensePillInactive]}>
      <Text style={styles.licenseStatus}>{active ? entitlement?.status === "active" ? "LICENCIA ACTIVA" : "PRUEBA HABILITADA" : "LICENCIA INACTIVA"}</Text>
      <Text style={styles.licenseName}>{entitlement?.plan_name || "Fuego & Humo"}</Text>
      <Text style={styles.licenseDate}>{entitlement?.expires_at ? `Hasta ${new Date(entitlement.expires_at).toLocaleDateString("es-AR")}` : "Sin vencimiento"}</Text>
    </View>
  );
}

function MiniFact({ icon, value, label }: { icon: string; value: string; label: string }) {
  return <View style={styles.miniFact}><Text style={styles.miniFactIcon}>{icon}</Text><Text style={styles.miniFactValue}>{value}</Text><Text style={styles.miniFactLabel}>{label}</Text></View>;
}

function PlainFact({ icon, title, text }: { icon: string; title: string; text: string }) {
  return <View style={styles.plainFact}><Text style={styles.plainFactIcon}>{icon}</Text><View style={styles.plainFactText}><Text style={styles.cardTitle}>{title}</Text><Text style={styles.bodyText}>{text}</Text></View></View>;
}

function AiAlertScreen({ session, bundle }: { session: Session; bundle: DashboardBundle }) {
  const snapshot = bundle.latestSnapshot?.snapshot || null;
  const [audience, setAudience] = useState<Audience>("medios");
  const [busy, setBusy] = useState(false);
  const topIndex = snapshot?.indices.slice().sort((a, b) => b.score - a.score)[0] || null;
  const alertMessage = useMemo(() => {
    if (!snapshot) return "EcoNexo no tiene todavía un snapshot ambiental para preparar una alerta.";
    const lines = [
      "⚠️ *EcoNexo · Alerta IA para revisión*",
      "",
      `Nivel integrado: *${snapshot.overall_level} · ${snapshot.overall_label}* (${snapshot.overall_score.toFixed(0)}/100).`,
      topIndex ? `Mayor señal: ${topIndex.label}, ${topIndex.level}, ${topIndex.status}.` : "",
      snapshot.alerts[0] ? `Situación: ${snapshot.alerts[0].summary}` : "",
      snapshot.alerts[0] ? `Acción sugerida: ${snapshot.alerts[0].action}` : "",
      "",
      `Zona: ${snapshot.latitude.toFixed(4)}, ${snapshot.longitude.toFixed(4)}.`,
      `Metodología: ${snapshot.methodology_version}.`,
      "",
      "Borrador generado por IA. Debe revisarse antes de difundir. No reemplaza una comunicación oficial ni una evaluación sanitaria.",
    ];
    return lines.filter(Boolean).join("\n");
  }, [snapshot, topIndex]);

  async function share(channel: "whatsapp" | "telegram" | "otro") {
    if (!snapshot || !bundle.latestSnapshot) return;
    setBusy(true);
    try {
      await registerAlertShare(session, {
        channel,
        audience,
        title: `Alerta IA ${snapshot.overall_level} · ${snapshot.overall_label}`,
        message: alertMessage,
        module_key: "core",
        snapshot_id: bundle.latestSnapshot.id,
        metadata: { overall_score: snapshot.overall_score, overall_level: snapshot.overall_level },
      });
      if (channel === "otro") await Share.share({ message: alertMessage, title: "EcoNexo · Alerta IA" });
      else {
        const encoded = encodeURIComponent(alertMessage);
        const url = channel === "whatsapp" ? `https://wa.me/?text=${encoded}` : `https://t.me/share/url?url=${encodeURIComponent("https://econexo.app")}&text=${encoded}`;
        await Linking.openURL(url);
      }
    } catch (cause) {
      NativeAlert.alert("No se pudo compartir", cause instanceof Error ? cause.message : "Error inesperado.");
    } finally { setBusy(false); }
  }

  if (!snapshot) return <ScrollView contentContainerStyle={styles.screenContent}><SectionHeader eyebrow="ALERTA IA" title="Inteligencia ambiental explicable" /><EmptyState title="Todavía no hay snapshot" text="Generá un análisis desde el Observatorio web para habilitar la lectura móvil y los mensajes de alerta." /></ScrollView>;

  return (
    <ScrollView contentContainerStyle={styles.screenContent}>
      <View style={styles.aiHero}>
        <Text style={styles.eyebrow}>ALERTA IA · BORRADOR PARA REVISIÓN</Text>
        <View style={styles.aiHeroRow}>
          <View style={[styles.aiScore, { borderColor: levelColor(snapshot.overall_level) }]}><Text style={[styles.aiScoreLevel, { color: levelColor(snapshot.overall_level) }]}>{snapshot.overall_level}</Text><Text style={styles.aiScoreValue}>{snapshot.overall_score.toFixed(0)}</Text><Text style={styles.aiScoreUnit}>/100</Text></View>
          <View style={styles.aiHeroText}><Text style={styles.heroTitle}>{snapshot.overall_label}</Text><Text style={styles.heroText}>Lectura multicapa con evidencia, fórmulas visibles y revisión humana antes de comunicar.</Text><Text style={styles.coordinates}>{snapshot.latitude.toFixed(4)}, {snapshot.longitude.toFixed(4)} · {relativeTime(snapshot.generated_at)}</Text></View>
        </View>
      </View>

      <SectionHeader eyebrow="ÍNDICES AMBIENTALES" title="Qué empuja la alerta" description="Cada dominio muestra nivel, confianza, evidencia y contribución al resultado integrado." />
      {snapshot.indices.map((index) => <IndexCard index={index} key={index.id} />)}

      <View style={styles.formulaCard}>
        <Text style={styles.eyebrow}>MÉTODO EXPLICABLE</Text>
        <Text style={styles.formula}>Excedencia (%) = valor observado / valor de referencia × 100</Text>
        <Text style={styles.formula}>Scoreᵢ = severidadᵢ × persistenciaᵢ × confiabilidadᵢ</Text>
        <Text style={styles.formula}>HTI = Σ(wᵢ × Scoreᵢ × vulnerabilidad poblacional) / Σ(wᵢ)</Text>
        <Text style={styles.muted}>R0 &lt;80% · R1 80–99% · R2 100–149% · R3 150–199% · R4 ≥200% · R5 por regla específica.</Text>
      </View>

      <View style={styles.shareCard}>
        <SectionHeader eyebrow="DISTRIBUCIÓN CONTROLADA" title="Mandar Alerta IA" description="Preparada para medios, organizaciones, laboratorios o emergencias. Siempre requiere aprobación humana." />
        <Text style={styles.label}>Destinatario</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalChoices}>
          {(["medios", "organizacion", "laboratorio", "emergencia", "publico"] as Audience[]).map((item) => (
            <Pressable key={item} onPress={() => setAudience(item)} style={[styles.choice, audience === item && styles.choiceActive]}><Text style={[styles.choiceText, audience === item && styles.choiceTextActive]}>{titleCase(item)}</Text></Pressable>
          ))}
        </ScrollView>
        <View style={styles.messagePreview}><Text selectable style={styles.messageText}>{alertMessage}</Text></View>
        <View style={styles.shareButtons}>
          <AppButton disabled={busy} onPress={() => void share("whatsapp")} variant="whatsapp">WhatsApp</AppButton>
          <AppButton disabled={busy} onPress={() => void share("telegram")} variant="telegram">Telegram</AppButton>
          <AppButton disabled={busy} onPress={() => void share("otro")} variant="secondary">Más opciones</AppButton>
        </View>
      </View>

      <View style={styles.legalCard}><Text style={styles.cardTitle}>Limitaciones visibles</Text>{snapshot.limitations.map((item) => <Text key={item} style={styles.bullet}>• {item}</Text>)}</View>
    </ScrollView>
  );
}

function IndexCard({ index }: { index: EnvironmentalIndex }) {
  return (
    <View style={styles.indexCard}>
      <View style={styles.cardTopRow}><View><Text style={styles.cardTitle}>{index.label}</Text><Text style={styles.muted}>{index.source}</Text></View><View style={[styles.levelChip, { borderColor: levelColor(index.level) }]}><Text style={[styles.levelChipText, { color: levelColor(index.level) }]}>{index.level}</Text></View></View>
      <View style={styles.progressTrack}><View style={[styles.progressValue, { width: `${Math.min(100, Math.max(0, index.score))}%`, backgroundColor: levelColor(index.level) }]} /></View>
      <Text style={styles.bodyText}>{index.status}</Text>
      <View style={styles.indexMetrics}><Text style={styles.metricText}>Score {index.score.toFixed(0)}</Text><Text style={styles.metricText}>Confianza {Math.round(index.confidence * 100)}%</Text>{index.relative_exceedance_pct != null ? <Text style={styles.metricText}>Excedencia {index.relative_exceedance_pct.toFixed(0)}%</Text> : null}</View>
      {index.evidence.slice(0, 3).map((item) => <Text key={item} style={styles.bullet}>• {item}</Text>)}
      {index.formula ? <Text style={styles.indexFormula}>{index.formula}</Text> : null}
    </View>
  );
}

function ReportScreen({ session, center, onCreated }: { session: Session; center: { latitude: number; longitude: number }; onCreated: () => Promise<void> }) {
  const [type, setType] = useState<ReportType>("humo");
  const [description, setDescription] = useState("");
  const [latitude, setLatitude] = useState(String(center.latitude));
  const [longitude, setLongitude] = useState(String(center.longitude));
  const [photo, setPhoto] = useState<MobileReportInput["photo"]>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setLatitude(String(center.latitude));
    setLongitude(String(center.longitude));
  }, [center.latitude, center.longitude]);

  async function useLocation() {
    setMessage("");
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") return setMessage("Necesitamos permiso de ubicación para georreferenciar el reporte.");
    const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
    if (!isInMisiones(position.coords.latitude, position.coords.longitude)) return setMessage("La ubicación está fuera de Misiones y no puede cargarse en este lanzamiento.");
    setLatitude(position.coords.latitude.toFixed(6));
    setLongitude(position.coords.longitude.toFixed(6));
    setMessage("Ubicación actual cargada dentro de Misiones.");
  }

  async function selectPhoto(fromCamera: boolean) {
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return setMessage("No se otorgó permiso para acceder a la imagen.");
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.82 })
      : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.82 });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setPhoto({ uri: asset.uri, fileName: asset.fileName, mimeType: asset.mimeType });
    }
  }

  async function submit() {
    const lat = Number(latitude);
    const lon = Number(longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return setMessage("Las coordenadas no son válidas.");
    if (!isInMisiones(lat, lon)) return setMessage("El reporte debe estar ubicado dentro de la provincia de Misiones.");
    if (!description.trim()) return setMessage("Contá brevemente qué viste.");
    setBusy(true); setMessage("");
    try {
      await submitInternalReport(session, { type, description, lat, lon, photo });
      setDescription(""); setPhoto(null);
      setMessage("Reporte enviado. Quedó pendiente de moderación y correlación.");
      await onCreated();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "No se pudo enviar el reporte.");
    } finally { setBusy(false); }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flex}>
      <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled">
        <SectionHeader eyebrow="REPORTE COMUNITARIO E INSTITUCIONAL" title="Contá qué está pasando" description="El formulario no publica automáticamente. El reporte queda georreferenciado, se correlaciona con otras señales y pasa por moderación." />
        <Text style={styles.label}>Tipo de evento</Text>
        <View style={styles.reportTypeGrid}>
          {(["humo", "incendio", "inundacion", "vertido", "otro"] as ReportType[]).map((item) => (
            <Pressable key={item} onPress={() => setType(item)} style={[styles.reportType, type === item && styles.reportTypeActive]}>
              <Text style={styles.reportTypeIcon}>{item === "humo" ? "🌫️" : item === "incendio" ? "🔥" : item === "inundacion" ? "🌊" : item === "vertido" ? "🧪" : "📍"}</Text>
              <Text style={[styles.choiceText, type === item && styles.choiceTextActive]}>{titleCase(item)}</Text>
            </Pressable>
          ))}
        </View>
        <Field label="Descripción" multiline onChangeText={setDescription} placeholder="Ej.: veo humo oscuro detrás del lote, hacia el norte…" value={description} />
        <View style={styles.coordinateRow}>
          <View style={styles.coordinateField}><Field keyboardType="decimal-pad" label="Latitud" onChangeText={setLatitude} placeholder="-27.3621" value={latitude} /></View>
          <View style={styles.coordinateField}><Field keyboardType="decimal-pad" label="Longitud" onChangeText={setLongitude} placeholder="-55.9007" value={longitude} /></View>
        </View>
        <AppButton onPress={() => void useLocation()} variant="secondary">Usar mi ubicación actual</AppButton>

        <View style={styles.photoCard}>
          <Text style={styles.cardTitle}>Evidencia fotográfica opcional</Text>
          <Text style={styles.muted}>No fotografíes personas identificables sin necesidad ni te acerques a una zona peligrosa.</Text>
          {photo ? <Image resizeMode="cover" source={{ uri: photo.uri }} style={styles.reportPhoto} /> : <View style={styles.photoPlaceholder}><Text style={styles.photoPlaceholderIcon}>＋</Text><Text style={styles.muted}>Sin imagen seleccionada</Text></View>}
          <View style={styles.photoActions}><AppButton onPress={() => void selectPhoto(true)} variant="secondary">Cámara</AppButton><AppButton onPress={() => void selectPhoto(false)} variant="secondary">Galería</AppButton></View>
        </View>
        <AppButton disabled={busy} onPress={() => void submit()}>{busy ? "Enviando…" : "Enviar reporte para revisión"}</AppButton>
        {message ? <View style={message.startsWith("Reporte enviado") || message.includes("cargada") ? styles.successBox : styles.infoBox}><Text style={styles.bodyText}>{message}</Text></View> : null}
        <View style={styles.legalCard}><Text style={styles.cardTitle}>Emergencias</Text><Text style={styles.bodyText}>Este formulario no reemplaza una llamada. Si hay fuego, personas en riesgo o una amenaza inmediata, alejate y llamá al 911.</Text></View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function AccountScreen({ session, bundle, onLogout }: { session: Session; bundle: DashboardBundle; onLogout: () => Promise<void> }) {
  return (
    <ScrollView contentContainerStyle={styles.screenContent}>
      <View style={styles.profileCard}>
        <Image resizeMode="contain" source={BRAND} style={styles.profileLogo} />
        <Text style={styles.heroTitle}>{session.name}</Text>
        <Text style={styles.muted}>{session.email}</Text>
        <View style={styles.profileTags}><Text style={styles.profileTag}>{session.role.toUpperCase()}</Text><Text style={styles.profileTag}>{session.auth_provider === "google" ? "GOOGLE" : "EMAIL"}</Text></View>
      </View>
      <SectionHeader eyebrow="ORGANIZACIÓN" title={bundle.org.name} description={`${titleCase(bundle.org.vertical)} · ${bundle.org.slug}`} />
      <View style={styles.settingsCard}>
        <SettingRow label="API" value={API_URL} />
        <SettingRow label="Modo" value={DEMO_MODE ? "Demo autónoma" : "API persistente"} />
        <SettingRow label="Sesión" value="SecureStore" />
        <SettingRow label="Nodos" value={`${bundle.devices.length}`} />
      </View>
      <SectionHeader eyebrow="LICENCIAS" title="Módulos habilitados" />
      {bundle.modules.map((module) => (
        <View key={module.module_key} style={styles.moduleRow}>
          <View style={[styles.deviceDot, module.available ? styles.deviceOnline : styles.deviceOffline]} />
          <View style={styles.deviceText}><Text style={styles.cardTitle}>{module.plan_name}</Text><Text style={styles.muted}>{module.status} · {module.expires_at ? `vence ${new Date(module.expires_at).toLocaleDateString("es-AR")}` : "sin vencimiento"}</Text></View>
        </View>
      ))}
      <View style={styles.legalCard}><Text style={styles.cardTitle}>Privacidad móvil</Text><Text style={styles.bodyText}>La sesión se almacena cifrada en SecureStore. La ubicación se solicita solo cuando cargás un reporte. EcoNexo no realiza seguimiento de ubicación en segundo plano.</Text></View>
      <AppButton onPress={() => void onLogout()} variant="danger">Cerrar sesión</AppButton>
    </ScrollView>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return <View style={styles.settingRow}><Text style={styles.muted}>{label}</Text><Text selectable style={styles.settingValue}>{value}</Text></View>;
}

function AlertActions({ session, alert, onClose, onDone }: { session: Session; alert: Alert; onClose: () => void; onDone: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  async function action(value: "confirmar" | "descartar" | "escalar") {
    setBusy(true);
    try {
      await actOnAlert(session, alert.id, value);
      await onDone();
      onClose();
    } catch (cause) {
      NativeAlert.alert("No se pudo actualizar", cause instanceof Error ? cause.message : "Error inesperado.");
    } finally { setBusy(false); }
  }
  return (
    <View style={styles.modalBackdrop}>
      <View style={styles.modalCard}>
        <View style={styles.cardTopRow}><Text style={styles.heroTitle}>{alert.title}</Text><Pressable onPress={onClose}><Text style={styles.closeButton}>×</Text></Pressable></View>
        <Text style={styles.bodyText}>Tipo: {titleCase(alert.type)} · Severidad: {alert.severity} · Confianza: {Math.round(alert.confidence * 100)}%</Text>
        <Text style={styles.coordinates}>{alert.lat.toFixed(5)}, {alert.lon.toFixed(5)}</Text>
        <View style={styles.modalActions}><AppButton disabled={busy} onPress={() => void action("confirmar")}>Confirmar</AppButton><AppButton disabled={busy} onPress={() => void action("escalar")} variant="secondary">Escalar</AppButton><AppButton disabled={busy} onPress={() => void action("descartar")} variant="danger">Descartar</AppButton></View>
      </View>
    </View>
  );
}

function MobileShell({ session, onLogout }: { session: Session; onLogout: () => Promise<void> }) {
  const [tab, setTab] = useState<AppTab>("inicio");
  const [bundle, setBundle] = useState<DashboardBundle | null>(null);
  const [earth, setEarth] = useState<EarthNow | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const center = useMemo(() => {
    const first = bundle?.devices.find((item) => isInMisiones(item.lat, item.lon));
    const snapshot = bundle?.latestSnapshot?.snapshot;
    return first
      ? { latitude: first.lat, longitude: first.lon }
      : snapshot
        ? { latitude: snapshot.latitude, longitude: snapshot.longitude }
        : DEFAULT_CENTER;
  }, [bundle]);

  const refresh = useCallback(async (isPull = false) => {
    if (isPull) setRefreshing(true); else setLoading(true);
    setError("");
    try {
      const next = await getDashboardBundle(session);
      setBundle(next);
      const firstLocalDevice = next.devices.find((item) => isInMisiones(item.lat, item.lon));
      const nextCenter = firstLocalDevice
        ? { latitude: firstLocalDevice.lat, longitude: firstLocalDevice.lon }
        : next.latestSnapshot
          ? { latitude: next.latestSnapshot.snapshot.latitude, longitude: next.latestSnapshot.snapshot.longitude }
          : DEFAULT_CENTER;
      try { setEarth(await fetchEarthNow(nextCenter.latitude, nextCenter.longitude)); }
      catch (cause) { setEarth(null); setError(cause instanceof Error ? cause.message : "No se pudo consultar el contexto ambiental."); }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo cargar EcoNexo.");
    } finally {
      setLoading(false); setRefreshing(false);
    }
  }, [session]);

  useEffect(() => { void refresh(); }, [refresh]);

  if (loading && !bundle) return <SafeAreaView style={styles.loadingSafe}><Image resizeMode="contain" source={BRAND} style={styles.loadingLogo} /><ActivityIndicator color={colors.cyan} size="large" /><Text style={styles.muted}>Sincronizando centro de comando…</Text></SafeAreaView>;

  if (!bundle) return <SafeAreaView style={styles.loadingSafe}><Text style={styles.errorTitle}>No se pudo abrir EcoNexo</Text><Text style={styles.muted}>{error}</Text><AppButton onPress={() => void refresh()}>Reintentar</AppButton><AppButton onPress={() => void onLogout()} variant="secondary">Volver al acceso</AppButton></SafeAreaView>;

  return (
    <SafeAreaView edges={["top", "left", "right"]} style={styles.appSafe}>
      <View style={styles.topBar}>
        <Image resizeMode="contain" source={BRAND} style={styles.topLogo} />
        <View style={styles.topOrg}><Text numberOfLines={1} style={styles.topOrgName}>{bundle.org.name}</Text><Text style={styles.topOrgMeta}>{DEMO_MODE ? "DEMO" : "EN LÍNEA"} · {session.role}</Text></View>
        <Pressable onPress={() => void refresh(true)} style={styles.syncButton}><Text style={styles.syncIcon}>↻</Text></Pressable>
      </View>
      {error ? <View style={styles.warningBar}><Text style={styles.warningText}>{error}</Text></View> : null}
      <View style={styles.contentArea}>
        {tab === "inicio" ? <HomeScreen bundle={bundle} earth={earth} onRefresh={() => void refresh(true)} onSelectAlert={setSelectedAlert} refreshing={refreshing} /> : null}
        {tab === "fuego" ? <FireScreen bundle={bundle} center={center} earth={earth} onRefresh={() => void refresh(true)} refreshing={refreshing} session={session} /> : null}
        {tab === "ia" ? <AiAlertScreen bundle={bundle} session={session} /> : null}
        {tab === "reportar" ? <ReportScreen center={center} onCreated={async () => refresh(true)} session={session} /> : null}
        {tab === "cuenta" ? <AccountScreen bundle={bundle} onLogout={onLogout} session={session} /> : null}
      </View>
      <View style={styles.bottomNav}>
        <NavItem active={tab === "inicio"} icon="⌂" label="Inicio" onPress={() => setTab("inicio")} />
        <NavItem active={tab === "fuego"} icon="🔥" label="Fuego" onPress={() => setTab("fuego")} />
        <NavItem active={tab === "ia"} icon="✦" label="Alerta IA" onPress={() => setTab("ia")} />
        <NavItem active={tab === "reportar"} icon="＋" label="Reportar" onPress={() => setTab("reportar")} />
        <NavItem active={tab === "cuenta"} icon="◉" label="Cuenta" onPress={() => setTab("cuenta")} />
      </View>
      {selectedAlert ? <AlertActions alert={selectedAlert} onClose={() => setSelectedAlert(null)} onDone={async () => refresh(true)} session={session} /> : null}
    </SafeAreaView>
  );
}

function NavItem({ active, icon, label, onPress }: { active: boolean; icon: string; label: string; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="tab" accessibilityState={{ selected: active }} onPress={onPress} style={styles.navItem}>
      <View style={[styles.navIconWrap, active && styles.navIconWrapActive]}><Text style={[styles.navIcon, active && styles.navIconActive]}>{icon}</Text></View>
      <Text style={[styles.navLabel, active && styles.navLabelActive]}>{label}</Text>
    </Pressable>
  );
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [restoring, setRestoring] = useState(true);

  useEffect(() => {
    void loadSession().then(setSession).finally(() => setRestoring(false));
  }, []);

  const authenticated = useCallback(async (next: Session) => {
    await saveSession(next);
    setSession(next);
  }, []);

  const logout = useCallback(async () => {
    await clearSession();
    setSession(null);
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      {restoring ? <SafeAreaView style={styles.loadingSafe}><Image resizeMode="contain" source={BRAND} style={styles.loadingLogo} /><ActivityIndicator color={colors.cyan} size="large" /></SafeAreaView>
        : session ? <MobileShell onLogout={logout} session={session} /> : <AuthScreen onAuthenticated={authenticated} />}
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  authSafe: { flex: 1, backgroundColor: colors.background },
  authScroll: { flexGrow: 1, justifyContent: "center", padding: spacing.lg },
  authCard: { backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.lg, borderWidth: 1, padding: spacing.xl, gap: spacing.md },
  authLogo: { alignSelf: "center", height: 92, width: "78%" },
  connectionPill: { alignItems: "center", backgroundColor: "#0b2d20", borderColor: "#2a7a52", borderRadius: radii.md, borderWidth: 1, flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  connectionPillError: { backgroundColor: "#321615", borderColor: colors.red },
  connectionDot: { backgroundColor: colors.green, borderRadius: 6, height: 8, shadowColor: colors.green, shadowOpacity: 0.8, shadowRadius: 6, width: 8 },
  connectionDotError: { backgroundColor: colors.red, shadowColor: colors.red },
  connectionText: { color: colors.text, fontSize: 12, fontWeight: "700", letterSpacing: 0.5 },
  segmented: { backgroundColor: colors.black, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, flexDirection: "row", padding: 3 },
  segment: { alignItems: "center", borderRadius: radii.sm, flex: 1, paddingVertical: 9 },
  segmentActive: { backgroundColor: "#17351f", borderColor: "#4d8e3d", borderWidth: 1 },
  segmentText: { color: colors.muted, fontSize: 12, fontWeight: "700" },
  segmentTextActive: { color: colors.white },
  sectionHeader: { gap: 5, marginBottom: spacing.sm, marginTop: spacing.md },
  eyebrow: { color: colors.cyan, fontSize: 10, fontWeight: "800", letterSpacing: 1.4 },
  sectionTitle: { color: colors.text, fontSize: 23, fontWeight: "800", letterSpacing: -0.5 },
  sectionDescription: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  fieldWrap: { gap: 6 },
  label: { color: colors.muted, fontSize: 12, fontWeight: "700" },
  input: { backgroundColor: colors.black, borderColor: colors.border, borderRadius: radii.sm, borderWidth: 1, color: colors.text, fontSize: 15, minHeight: 48, paddingHorizontal: spacing.md, paddingVertical: 11 },
  textarea: { minHeight: 120, textAlignVertical: "top" },
  choiceRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  choice: { backgroundColor: colors.black, borderColor: colors.border, borderRadius: radii.pill, borderWidth: 1, paddingHorizontal: spacing.md, paddingVertical: 9 },
  choiceActive: { backgroundColor: "#17351f", borderColor: colors.green },
  choiceText: { color: colors.muted, fontSize: 12, fontWeight: "700" },
  choiceTextActive: { color: colors.text },
  termsRow: { alignItems: "center", flexDirection: "row", gap: spacing.sm },
  termsText: { color: colors.text, flex: 1, fontSize: 12, lineHeight: 18 },
  button: { alignItems: "center", backgroundColor: colors.green, borderRadius: radii.sm, justifyContent: "center", minHeight: 48, paddingHorizontal: spacing.md },
  buttonSecondary: { backgroundColor: colors.backgroundRaised, borderColor: colors.borderBright, borderWidth: 1 },
  buttonDanger: { backgroundColor: "#8f2b2b" },
  buttonWhatsApp: { backgroundColor: "#25D366" },
  buttonTelegram: { backgroundColor: "#229ED9" },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.8, transform: [{ scale: 0.99 }] },
  buttonText: { color: colors.black, fontSize: 14, fontWeight: "900" },
  buttonTextSecondary: { color: colors.text },
  dividerRow: { alignItems: "center", flexDirection: "row", gap: spacing.sm, marginVertical: spacing.sm },
  divider: { backgroundColor: colors.border, flex: 1, height: 1 },
  dividerText: { color: colors.muted, fontSize: 9, fontWeight: "800", letterSpacing: 1 },
  helperText: { color: colors.muted, fontSize: 11, lineHeight: 17, textAlign: "center" },
  errorBox: { backgroundColor: "#301413", borderColor: colors.red, borderRadius: radii.sm, borderWidth: 1, padding: spacing.md },
  errorText: { color: "#ffc4bf", fontSize: 12, lineHeight: 18 },
  apiText: { color: "#58736d", fontSize: 9, textAlign: "center" },
  loadingSafe: { alignItems: "center", backgroundColor: colors.background, flex: 1, gap: spacing.lg, justifyContent: "center", padding: spacing.xl },
  loadingLogo: { height: 120, width: 260 },
  errorTitle: { color: colors.red, fontSize: 22, fontWeight: "800", textAlign: "center" },
  appSafe: { backgroundColor: colors.background, flex: 1 },
  topBar: { alignItems: "center", backgroundColor: colors.backgroundRaised, borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", minHeight: 62, paddingHorizontal: spacing.md },
  topLogo: { height: 50, width: 128 },
  topOrg: { flex: 1, paddingHorizontal: spacing.sm },
  topOrgName: { color: colors.text, fontSize: 14, fontWeight: "800" },
  topOrgMeta: { color: colors.green, fontSize: 9, fontWeight: "800", letterSpacing: 1 },
  syncButton: { alignItems: "center", backgroundColor: colors.panel, borderColor: colors.border, borderRadius: 20, borderWidth: 1, height: 40, justifyContent: "center", width: 40 },
  syncIcon: { color: colors.cyan, fontSize: 22 },
  warningBar: { backgroundColor: "#392d12", borderBottomColor: colors.yellow, borderBottomWidth: 1, paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  warningText: { color: "#ffe6a1", fontSize: 11, lineHeight: 16 },
  contentArea: { flex: 1 },
  screenContent: { gap: spacing.md, padding: spacing.md, paddingBottom: 130 },
  heroCard: { backgroundColor: colors.panel, borderColor: colors.borderBright, borderRadius: radii.lg, borderWidth: 1, gap: spacing.sm, overflow: "hidden", padding: spacing.xl },
  heroTitle: { color: colors.text, fontSize: 25, fontWeight: "900", letterSpacing: -0.7 },
  heroText: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  heroStatusRow: { alignItems: "center", flexDirection: "row", gap: spacing.lg, marginTop: spacing.md },
  statusOrb: { alignItems: "center", borderRadius: 48, borderWidth: 2, height: 92, justifyContent: "center", width: 92 },
  statusOrbValue: { color: colors.text, fontSize: 28, fontWeight: "900" },
  statusOrbLabel: { color: colors.muted, fontSize: 10, textTransform: "uppercase" },
  heroStatusCopy: { flex: 1, gap: 5 },
  heroStatusTitle: { color: colors.text, fontSize: 18, fontWeight: "800" },
  muted: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  bodyText: { color: colors.text, fontSize: 14, lineHeight: 21 },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  kpiCard: { backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, minHeight: 104, padding: spacing.md, width: "48.5%" },
  kpiLabel: { color: colors.muted, fontSize: 11, fontWeight: "700" },
  kpiValue: { color: colors.cyan, fontSize: 25, fontWeight: "900", marginTop: 6 },
  kpiDetail: { color: colors.muted, fontSize: 10, marginTop: 4 },
  alertCard: { backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, flexDirection: "row", overflow: "hidden" },
  severityLine: { width: 5 },
  alertBody: { flex: 1, gap: 6, padding: spacing.md },
  cardTopRow: { alignItems: "flex-start", flexDirection: "row", gap: spacing.md, justifyContent: "space-between" },
  cardTitle: { color: colors.text, flexShrink: 1, fontSize: 16, fontWeight: "800" },
  badge: { borderRadius: radii.pill, borderWidth: 1, fontSize: 9, fontWeight: "900", paddingHorizontal: 8, paddingVertical: 4 },
  coordinates: { color: colors.cyan, fontFamily: Platform.select({ ios: "Menlo", android: "monospace" }), fontSize: 11 },
  deviceCard: { alignItems: "center", backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, flexDirection: "row", gap: spacing.md, padding: spacing.md },
  deviceDot: { borderRadius: 6, height: 10, width: 10 },
  deviceOnline: { backgroundColor: colors.green },
  deviceOffline: { backgroundColor: colors.red },
  deviceText: { flex: 1, gap: 3 },
  deviceBattery: { color: colors.text, fontSize: 13, fontWeight: "800", textAlign: "right" },
  deviceLastSeen: { color: colors.muted, fontSize: 9, textAlign: "right" },
  emptyCard: { alignItems: "center", backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderStyle: "dashed", borderWidth: 1, gap: spacing.sm, padding: spacing.xl },
  emptyIcon: { color: colors.cyan, fontSize: 36 },
  moduleHeader: { backgroundColor: colors.panel, borderColor: colors.borderBright, borderRadius: radii.lg, borderWidth: 1, gap: spacing.md, padding: spacing.xl },
  moduleHeaderText: { gap: spacing.sm },
  licensePill: { backgroundColor: "#102f20", borderColor: colors.green, borderRadius: radii.md, borderWidth: 1, gap: 3, padding: spacing.md },
  licensePillInactive: { backgroundColor: "#321615", borderColor: colors.red },
  licenseStatus: { color: colors.green, fontSize: 9, fontWeight: "900", letterSpacing: 1.2 },
  licenseName: { color: colors.text, fontSize: 14, fontWeight: "800" },
  licenseDate: { color: colors.muted, fontSize: 10 },
  publicStatus: { alignItems: "center", backgroundColor: colors.backgroundRaised, borderRadius: radii.lg, borderWidth: 2, flexDirection: "row", gap: spacing.md, padding: spacing.lg },
  publicStatusIcon: { alignItems: "center", borderRadius: 35, borderWidth: 2, height: 70, justifyContent: "center", width: 70 },
  publicStatusIconText: { fontSize: 32, fontWeight: "900" },
  publicStatusText: { flex: 1, gap: 6 },
  publicHeadline: { color: colors.text, fontSize: 19, fontWeight: "900", lineHeight: 24 },
  quickGrid: { flexDirection: "row", gap: spacing.sm },
  miniFact: { alignItems: "center", backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, flex: 1, gap: 3, padding: spacing.md },
  miniFactIcon: { fontSize: 20 },
  miniFactValue: { color: colors.text, fontSize: 21, fontWeight: "900" },
  miniFactLabel: { color: colors.muted, fontSize: 9, textAlign: "center" },
  mapFrame: { backgroundColor: colors.black, borderColor: colors.border, borderRadius: radii.lg, borderWidth: 1, overflow: "hidden" },
  map: { height: 330, width: "100%" },
  mapLegend: { backgroundColor: "rgba(3,20,19,.92)", bottom: 10, flexDirection: "row", gap: spacing.md, left: 10, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, position: "absolute", borderRadius: radii.pill },
  mapLegendText: { color: colors.green, fontSize: 10, fontWeight: "800" },
  plainFact: { alignItems: "flex-start", backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, flexDirection: "row", gap: spacing.md, padding: spacing.md },
  plainFactIcon: { fontSize: 25 },
  plainFactText: { flex: 1, gap: 5 },
  shareCard: { backgroundColor: colors.panel, borderColor: colors.borderBright, borderRadius: radii.lg, borderWidth: 1, gap: spacing.md, padding: spacing.lg },
  horizontalChoices: { flexGrow: 0 },
  messagePreview: { backgroundColor: colors.black, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, maxHeight: 330, padding: spacing.md },
  messageText: { color: colors.text, fontSize: 13, lineHeight: 20 },
  shareButtons: { gap: spacing.sm },
  legalCard: { backgroundColor: "#0a2824", borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, gap: spacing.sm, padding: spacing.lg },
  bullet: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  aiHero: { backgroundColor: colors.panel, borderColor: colors.purple, borderRadius: radii.lg, borderWidth: 1, gap: spacing.md, padding: spacing.xl },
  aiHeroRow: { alignItems: "center", flexDirection: "row", gap: spacing.lg },
  aiScore: { alignItems: "center", borderRadius: 55, borderWidth: 2, height: 110, justifyContent: "center", width: 110 },
  aiScoreLevel: { fontSize: 15, fontWeight: "900" },
  aiScoreValue: { color: colors.text, fontSize: 31, fontWeight: "900" },
  aiScoreUnit: { color: colors.muted, fontSize: 10 },
  aiHeroText: { flex: 1, gap: 5 },
  indexCard: { backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, gap: spacing.sm, padding: spacing.lg },
  levelChip: { alignItems: "center", borderRadius: radii.pill, borderWidth: 1, minWidth: 48, paddingHorizontal: spacing.sm, paddingVertical: 6 },
  levelChipText: { fontSize: 12, fontWeight: "900" },
  progressTrack: { backgroundColor: colors.black, borderRadius: 4, height: 7, overflow: "hidden" },
  progressValue: { borderRadius: 4, height: "100%" },
  indexMetrics: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  metricText: { backgroundColor: colors.panel, borderRadius: radii.pill, color: colors.text, fontSize: 10, paddingHorizontal: 9, paddingVertical: 5 },
  indexFormula: { backgroundColor: colors.black, borderColor: colors.border, borderRadius: radii.sm, borderWidth: 1, color: colors.cyan, fontFamily: Platform.select({ ios: "Menlo", android: "monospace" }), fontSize: 11, lineHeight: 17, padding: spacing.sm },
  formulaCard: { backgroundColor: "#17122b", borderColor: colors.purple, borderRadius: radii.lg, borderWidth: 1, gap: spacing.sm, padding: spacing.lg },
  formula: { color: "#d9c9ff", fontFamily: Platform.select({ ios: "Menlo", android: "monospace" }), fontSize: 12, lineHeight: 19 },
  reportTypeGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  reportType: { alignItems: "center", backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, gap: 4, padding: spacing.md, width: "31.5%" },
  reportTypeActive: { backgroundColor: "#17351f", borderColor: colors.green },
  reportTypeIcon: { fontSize: 24 },
  coordinateRow: { flexDirection: "row", gap: spacing.sm },
  coordinateField: { flex: 1 },
  photoCard: { backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, gap: spacing.md, padding: spacing.lg },
  reportPhoto: { borderRadius: radii.md, height: 230, width: "100%" },
  photoPlaceholder: { alignItems: "center", borderColor: colors.border, borderRadius: radii.md, borderStyle: "dashed", borderWidth: 1, gap: spacing.sm, height: 160, justifyContent: "center" },
  photoPlaceholderIcon: { color: colors.cyan, fontSize: 38 },
  photoActions: { gap: spacing.sm },
  successBox: { backgroundColor: "#123421", borderColor: colors.green, borderRadius: radii.md, borderWidth: 1, padding: spacing.md },
  infoBox: { backgroundColor: "#172f35", borderColor: colors.blue, borderRadius: radii.md, borderWidth: 1, padding: spacing.md },
  profileCard: { alignItems: "center", backgroundColor: colors.panel, borderColor: colors.borderBright, borderRadius: radii.lg, borderWidth: 1, gap: spacing.sm, padding: spacing.xl },
  profileLogo: { height: 85, width: 230 },
  profileTags: { flexDirection: "row", gap: spacing.sm },
  profileTag: { backgroundColor: colors.black, borderColor: colors.border, borderRadius: radii.pill, borderWidth: 1, color: colors.cyan, fontSize: 9, fontWeight: "900", paddingHorizontal: spacing.sm, paddingVertical: 5 },
  settingsCard: { backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, overflow: "hidden" },
  settingRow: { alignItems: "center", borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: "row", gap: spacing.md, justifyContent: "space-between", padding: spacing.md },
  settingValue: { color: colors.text, flex: 1, fontSize: 12, fontWeight: "700", textAlign: "right" },
  moduleRow: { alignItems: "center", backgroundColor: colors.backgroundRaised, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, flexDirection: "row", gap: spacing.md, padding: spacing.md },
  bottomNav: { alignItems: "center", backgroundColor: "#061b19", borderTopColor: colors.border, borderTopWidth: 1, bottom: 0, flexDirection: "row", height: 78, left: 0, paddingBottom: Platform.OS === "ios" ? 8 : 4, position: "absolute", right: 0 },
  navItem: { alignItems: "center", flex: 1, gap: 2, justifyContent: "center" },
  navIconWrap: { alignItems: "center", borderRadius: 17, height: 34, justifyContent: "center", width: 40 },
  navIconWrapActive: { backgroundColor: "#173a31" },
  navIcon: { color: colors.muted, fontSize: 19 },
  navIconActive: { color: colors.green },
  navLabel: { color: colors.muted, fontSize: 9, fontWeight: "700" },
  navLabelActive: { color: colors.text },
  modalBackdrop: { alignItems: "center", backgroundColor: "rgba(0,0,0,.72)", bottom: 0, justifyContent: "center", left: 0, padding: spacing.lg, position: "absolute", right: 0, top: 0, zIndex: 100 },
  modalCard: { backgroundColor: colors.backgroundRaised, borderColor: colors.borderBright, borderRadius: radii.lg, borderWidth: 1, gap: spacing.md, padding: spacing.xl, width: "100%" },
  closeButton: { color: colors.muted, fontSize: 30, lineHeight: 30 },
  modalActions: { gap: spacing.sm },
});
