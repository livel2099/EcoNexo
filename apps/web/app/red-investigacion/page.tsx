"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { clearSession, getSession } from "../lib/api";
import type { Session } from "../lib/types";
import {
  createFoiComment,
  createFoiPost,
  deleteFoiPost,
  downloadFoiFile,
  fetchFoiComments,
  fetchFoiCommunities,
  fetchFoiPosts,
  fetchFoiProfile,
  fetchFoiSuggestions,
  toggleFoiCommunity,
  toggleFoiFollow,
  toggleFoiLike,
  toggleFoiSave,
  uploadFoiFile,
  type FoiAuthor,
  type FoiComment,
  type FoiCommunity,
  type FoiPost,
  type FoiPostKind,
  type FoiProfile,
} from "./foi-api";
import styles from "./research-network.module.css";

type IconName = "home" | "compass" | "users" | "bookmark" | "bell" | "search" | "plus" | "arrow" | "back" | "heart" | "message" | "share" | "more" | "file" | "flask" | "check" | "close" | "image" | "link" | "chevron" | "lock" | "logout";

function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    home: <><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10M9 20v-6h6v6"/></>,
    compass: <><circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    bookmark: <path d="M6 3h12v18l-6-4-6 4V3Z"/>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    back: <><path d="M19 12H5M11 18l-6-6 6-6"/></>,
    heart: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/>,
    message: <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z"/>,
    share: <><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 10.5 6.8-4M8.6 13.5l6.8 4"/></>,
    more: <><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/></>,
    file: <><path d="M6 2h8l4 4v16H6V2Z"/><path d="M14 2v5h5M9 13h6M9 17h5"/></>,
    flask: <><path d="M9 3h6M10 3v6l-5.4 9.4A1.7 1.7 0 0 0 6.1 21h11.8a1.7 1.7 0 0 0 1.5-2.6L14 9V3"/><path d="M7.5 15h9"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    close: <><path d="m6 6 12 12M18 6 6 18"/></>,
    image: <><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/></>,
    link: <><path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3"/><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

const kindMeta: Record<FoiPostKind, { label: string; icon: IconName; className: string }> = {
  research: { label: "Investigación", icon: "file", className: "" },
  question: { label: "Pregunta abierta", icon: "message", className: styles.kindBlue },
  proposal: { label: "Propuesta colaborativa", icon: "users", className: styles.kindGold },
};

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function relativeTime(value: string) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "Ahora";
  if (seconds < 3600) return `Hace ${Math.floor(seconds / 60)} min`;
  if (seconds < 86400) return `Hace ${Math.floor(seconds / 3600)} h`;
  if (seconds < 172800) return "Ayer";
  return new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "short" }).format(new Date(value));
}

export default function ResearchNetworkPage() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<FoiProfile | null>(null);
  const [posts, setPosts] = useState<FoiPost[]>([]);
  const [communities, setCommunities] = useState<FoiCommunity[]>([]);
  const [suggestions, setSuggestions] = useState<FoiAuthor[]>([]);
  const [activeNav, setActiveNav] = useState("Inicio");
  const [activeFeed, setActiveFeed] = useState("Para vos");
  const [selectedCommunity, setSelectedCommunity] = useState<string | undefined>();
  const [query, setQuery] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [openComments, setOpenComments] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, FoiComment[]>>({});
  const [commentDraft, setCommentDraft] = useState("");

  useEffect(() => {
    const current = getSession();
    if (!current) {
      router.replace("/login?next=/red-investigacion");
      return;
    }
    setSession(current);
  }, [router]);

  const loadPosts = useCallback(async (current: Session, search = query) => {
    const scope = activeNav === "Guardados" ? "saved" : activeFeed === "Siguiendo" ? "following" : "all";
    const data = await fetchFoiPosts(current.access_token, { q: search.trim(), scope, communityId: selectedCommunity });
    setPosts(data);
  }, [activeFeed, activeNav, query, selectedCommunity]);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all([
      loadPosts(session),
      fetchFoiCommunities(session.access_token),
      fetchFoiSuggestions(session.access_token),
      fetchFoiProfile(session.access_token),
    ]).then(([_, communityRows, people, me]) => {
      if (cancelled) return;
      setCommunities(communityRows);
      setSuggestions(people);
      setProfile(me);
    }).catch((cause) => {
      if (!cancelled) setError(cause instanceof Error ? cause.message : "No se pudo cargar EcoNexoFoI");
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [session, loadPosts]);

  useEffect(() => {
    if (!session) return;
    const timer = window.setTimeout(() => void loadPosts(session, query).catch((cause) => setError(cause instanceof Error ? cause.message : "No se pudo buscar")), 300);
    return () => window.clearTimeout(timer);
  }, [query, session, loadPosts]);

  const trending = useMemo(() => {
    const counts = new Map<string, number>();
    posts.forEach((post) => post.tags.forEach((tag) => counts.set(tag, (counts.get(tag) || 0) + 1)));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4);
  }, [posts]);

  function flash(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 3800);
  }

  async function submitPost(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setPublishing(true);
    setError("");
    try {
      const form = new FormData(event.currentTarget);
      const file = form.get("attachment");
      const upload = file instanceof File && file.size > 0 ? await uploadFoiFile(session.access_token, file) : null;
      await createFoiPost(session.access_token, {
        kind: String(form.get("kind")) as FoiPostKind,
        title: String(form.get("title")),
        abstract: String(form.get("abstract")),
        tags: String(form.get("tags") || "").split(",").map((tag) => tag.trim()).filter(Boolean),
        community_id: String(form.get("community_id") || "") || undefined,
        attachment_url: upload?.url,
        attachment_name: upload?.name,
        attachment_mime: upload?.mime,
      });
      event.currentTarget.reset();
      setComposerOpen(false);
      setActiveNav("Inicio");
      setActiveFeed("Recientes");
      await loadPosts(session, "");
      flash("Investigación publicada en EcoNexoFoI.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo publicar");
    } finally {
      setPublishing(false);
    }
  }

  async function toggleLike(post: FoiPost) {
    if (!session) return;
    const result = await toggleFoiLike(session.access_token, post.id);
    setPosts((current) => current.map((item) => item.id === post.id ? { ...item, liked: result.active, likes_count: result.count } : item));
  }

  async function toggleSave(post: FoiPost) {
    if (!session) return;
    const result = await toggleFoiSave(session.access_token, post.id);
    setPosts((current) => current.map((item) => item.id === post.id ? { ...item, saved: result.active } : item));
    if (activeNav === "Guardados" && !result.active) setPosts((current) => current.filter((item) => item.id !== post.id));
  }

  async function showComments(post: FoiPost) {
    if (!session) return;
    if (openComments === post.id) { setOpenComments(null); return; }
    setOpenComments(post.id);
    if (!comments[post.id]) {
      const rows = await fetchFoiComments(session.access_token, post.id);
      setComments((current) => ({ ...current, [post.id]: rows }));
    }
  }

  async function submitComment(event: FormEvent<HTMLFormElement>, post: FoiPost) {
    event.preventDefault();
    if (!session || !commentDraft.trim()) return;
    const created = await createFoiComment(session.access_token, post.id, commentDraft.trim());
    setComments((current) => ({ ...current, [post.id]: [...(current[post.id] || []), created] }));
    setPosts((current) => current.map((item) => item.id === post.id ? { ...item, comments_count: item.comments_count + 1 } : item));
    setCommentDraft("");
  }

  async function joinCommunity(community: FoiCommunity) {
    if (!session) return;
    const result = await toggleFoiCommunity(session.access_token, community.id);
    setCommunities((current) => current.map((item) => item.id === community.id ? { ...item, joined: result.active, members_count: result.count } : item));
  }

  async function followPerson(person: FoiAuthor) {
    if (!session) return;
    const result = await toggleFoiFollow(session.access_token, person.id);
    setSuggestions((current) => current.map((item) => item.id === person.id ? { ...item, followed: result.active } : item));
    setPosts((current) => current.map((post) => post.author.id === person.id ? { ...post, author: { ...post.author, followed: result.active } } : post));
  }

  async function removePost(post: FoiPost) {
    if (!session || !profile || post.author.id !== profile.id || !window.confirm("¿Eliminar esta publicación?")) return;
    await deleteFoiPost(session.access_token, post.id);
    setPosts((current) => current.filter((item) => item.id !== post.id));
    flash("Publicación eliminada.");
  }

  function selectNav(label: string) {
    setActiveNav(label);
    if (label !== "Comunidades") setSelectedCommunity(undefined);
    if (label === "Explorar") setActiveFeed("Recientes");
  }

  function logout() {
    clearSession();
    router.replace("/login");
  }

  const navItems: { label: string; icon: IconName }[] = [
    { label: "Inicio", icon: "home" }, { label: "Explorar", icon: "compass" },
    { label: "Comunidades", icon: "users" }, { label: "Guardados", icon: "bookmark" },
  ];

  return (
    <div className={styles.appShell}>
      <header className={styles.topbar}>
        <a className={styles.brand} href="/red-investigacion" aria-label="EcoNexoFoI, inicio"><img src="/red-investigacion/econexo-foi-logo.svg" alt="EcoNexoFoI — Foro de Investigación" /><small>beta</small></a>
        <label className={styles.searchBox}><Icon name="search" size={19}/><span className={styles.srOnly}>Buscar</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar investigaciones, personas o temas"/>{query && <button type="button" onClick={() => setQuery("")} aria-label="Limpiar"><Icon name="close" size={16}/></button>}<kbd>⌘ K</kbd></label>
        <div className={styles.headerActions}>
          <a className={styles.backHomeButton} href="/" aria-label="Volver al inicio de EcoNexo"><Icon name="back" size={18}/><span className={styles.backHomeLabel}>EcoNexo</span></a>
          <button className={styles.iconButton} aria-label="Notificaciones"><Icon name="bell" size={21}/><i/></button>
          <button className={styles.profileButton} aria-label="Perfil"><span className={`${styles.avatar} ${styles.avatarCurrent}`}>{initials(profile?.name || session?.name || "Usuario")}</span><span><b>{profile?.name || session?.name || "Cargando…"}</b><small>{profile?.headline || "EcoNexoFoI"}</small></span></button>
          <button className={styles.logoutButton} onClick={logout} aria-label="Cerrar sesión"><Icon name="logout" size={18}/></button>
        </div>
      </header>

      <div className={styles.pageGrid}>
        <aside className={styles.leftSidebar}>
          <nav className={styles.primaryNav} aria-label="Navegación principal">{navItems.map((item) => <button key={item.label} className={activeNav === item.label ? styles.navActive : ""} onClick={() => selectNav(item.label)}><Icon name={item.icon} size={20}/><span>{item.label}</span></button>)}</nav>
          <button className={styles.newPostButton} onClick={() => setComposerOpen(true)}><Icon name="plus" size={20}/>Publicar</button>
          <section className={styles.sidebarSection}>
            <div className={styles.sectionHeading}><span>Mis comunidades</span></div>
            {communities.filter((community) => community.joined).slice(0, 4).map((community) => <button key={community.id} className={styles.communityItem} onClick={() => { setActiveNav("Comunidades"); setSelectedCommunity(community.id); }}><span className={styles.communityIcon} style={{ color: community.color }}>{community.icon}</span><span><b>{community.name}</b><small>{community.posts_count} publicaciones</small></span></button>)}
            {!communities.some((community) => community.joined) && <p className={styles.sidebarEmpty}>Sumate a una comunidad desde el panel derecho.</p>}
          </section>
          <footer className={styles.sidebarFooter}>Acerca de · Principios · Privacidad<br/><span>© 2026 EcoNexoFoI</span></footer>
        </aside>

        <main className={styles.mainContent}>
          <section className={styles.welcomeCard}>
            <div><span className={styles.eyebrow}>CONOCIMIENTO SIN FRONTERAS</span><h1>Las mejores preguntas<br/>se responden <em>en comunidad.</em></h1><p>Publicá tus hallazgos, encontrá colaboradores y convertí una idea en el próximo proyecto colectivo.</p><div className={styles.welcomeActions}><button onClick={() => setComposerOpen(true)}>Compartir investigación <Icon name="arrow" size={17}/></button><button onClick={() => setActiveFeed("Recientes")}>Explorar temas</button></div></div>
            <div className={styles.orbitVisual} aria-hidden="true"><div className={styles.orbitOne}><span>CO₂</span><i/></div><div className={styles.orbitTwo}><span>∿</span><i/></div><div className={styles.core}><Icon name="flask" size={29}/></div><span className={styles.floatLabel}>{communities.reduce((sum, item) => sum + item.members_count, 0)} miembros en comunidades</span></div>
          </section>

          <div className={styles.feedHeader}><div className={styles.feedTabs}>{["Para vos", "Recientes", "Siguiendo"].map((tab) => <button key={tab} className={activeFeed === tab ? styles.feedTabActive : ""} onClick={() => setActiveFeed(tab)}>{tab}</button>)}</div><span>{posts.length} publicaciones</span></div>
          {error && <div className={styles.apiError} role="alert">{error}<button onClick={() => session && void loadPosts(session)}>Reintentar</button></div>}

          <section className={styles.feed} aria-live="polite">
            {loading && <div className={styles.loadingState}><i/><span>Conectando con la comunidad…</span></div>}
            {!loading && posts.length === 0 && <div className={styles.emptyState}><Icon name={activeNav === "Guardados" ? "bookmark" : "search"} size={30}/><h2>{activeNav === "Guardados" ? "Todavía no guardaste publicaciones" : "Este espacio está listo para la primera idea"}</h2><p>{activeNav === "Guardados" ? "Usá el marcador de cada publicación para armar tu biblioteca." : "Publicá una investigación, una pregunta o una propuesta colaborativa."}</p><button onClick={() => activeNav === "Guardados" ? selectNav("Inicio") : setComposerOpen(true)}>{activeNav === "Guardados" ? "Ver publicaciones" : "Crear publicación"}</button></div>}
            {posts.map((post, index) => {
              const meta = kindMeta[post.kind];
              const avatarClass = [styles.avatarEmerald, styles.avatarBlue, styles.avatarGold][index % 3];
              return <article className={styles.postCard} key={post.id}>
                <div className={styles.postAuthor}><span className={`${styles.avatar} ${avatarClass}`}>{initials(post.author.name)}</span><div><div><b>{post.author.name}</b><span className={styles.verified}><Icon name="check" size={10}/></span></div><p>{post.author.headline}{post.author.institution ? ` · ${post.author.institution}` : ""} · {relativeTime(post.created_at)}</p></div>{profile?.id === post.author.id ? <button className={styles.moreButton} onClick={() => void removePost(post)} aria-label="Eliminar publicación"><Icon name="close" size={18}/></button> : <button className={`${styles.inlineFollow} ${post.author.followed ? styles.following : ""}`} onClick={() => void followPerson(post.author)}>{post.author.followed ? "Siguiendo" : "Seguir"}</button>}</div>
                <span className={`${styles.kindBadge} ${meta.className}`}><Icon name={meta.icon} size={13}/>{meta.label}</span>
                <h2>{post.title}</h2><p className={styles.postText}>{post.abstract}</p>
                {post.attachment_url && <button type="button" className={styles.attachmentCard} onClick={() => session && void downloadFoiFile(session.access_token, post.attachment_url!, post.attachment_name || "investigacion").catch((cause) => setError(cause instanceof Error ? cause.message : "No se pudo descargar"))}><Icon name="file" size={22}/><span><b>{post.attachment_name || "Archivo de investigación"}</b><small>{post.attachment_mime || "Documento adjunto"}</small></span><Icon name="arrow" size={18}/></button>}
                {post.community && <button className={styles.postCommunity} onClick={() => { setActiveNav("Comunidades"); setSelectedCommunity(post.community?.id); }}><span style={{ color: post.community.color }}>{post.community.icon}</span>{post.community.name}</button>}
                <div className={styles.tagRow}>{post.tags.map((tag) => <button key={tag} onClick={() => setQuery(tag)}>#{tag.replaceAll(" ", "")}</button>)}</div>
                <div className={styles.postActions}><button className={post.liked ? styles.liked : ""} onClick={() => void toggleLike(post)} aria-pressed={post.liked}><Icon name="heart" size={19}/><span>{post.likes_count}</span></button><button onClick={() => void showComments(post)}><Icon name="message" size={18}/><span>{post.comments_count}</span></button><button onClick={() => navigator.clipboard?.writeText(`${window.location.origin}/red-investigacion?post=${post.id}`).then(() => flash("Enlace copiado."))} aria-label="Compartir"><Icon name="share" size={18}/></button><button className={`${styles.saveAction} ${post.saved ? styles.saved : ""}`} onClick={() => void toggleSave(post)} aria-pressed={post.saved} aria-label="Guardar"><Icon name="bookmark" size={19}/></button></div>
                {openComments === post.id && <div className={styles.commentsPanel}><div className={styles.commentsList}>{(comments[post.id] || []).map((comment) => <article key={comment.id}><span className={`${styles.avatar} ${styles.avatarBlue}`}>{initials(comment.author.name)}</span><div><b>{comment.author.name}</b><p>{comment.body}</p><small>{relativeTime(comment.created_at)}</small></div></article>)}{comments[post.id]?.length === 0 && <p className={styles.noComments}>Sé la primera persona en aportar a esta conversación.</p>}</div><form onSubmit={(event) => void submitComment(event, post)}><input value={commentDraft} onChange={(event) => setCommentDraft(event.target.value)} minLength={2} maxLength={4000} placeholder="Escribí una respuesta constructiva…" required/><button>Responder</button></form></div>}
              </article>;
            })}
          </section>
        </main>

        <aside className={styles.rightSidebar}>
          <section className={styles.sideCard}><div className={styles.sideTitle}><span>Comunidades abiertas</span></div><div className={styles.trendList}>{communities.slice(0, 4).map((community, index) => <div className={styles.communityJoinRow} key={community.id}><button onClick={() => { setActiveNav("Comunidades"); setSelectedCommunity(community.id); }}><span style={{ background: community.color }}>{community.icon || String(index + 1).padStart(2, "0")}</span><div><b>{community.name}</b><small>{community.members_count} miembros · {community.posts_count} publicaciones</small></div></button><button className={community.joined ? styles.joinedMini : ""} onClick={() => void joinCommunity(community)}>{community.joined ? "Unido" : "Unirme"}</button></div>)}</div></section>
          <section className={`${styles.sideCard} ${styles.challengeCard}`}><span className={styles.challengeLabel}>DESAFÍO ABIERTO</span><div className={styles.challengeIcon}>⌁</div><h2>¿Cómo hacemos ciudades más frescas?</h2><p>Compartí soluciones basadas en naturaleza para mitigar islas de calor.</p><div className={styles.challengeMeta}><span><b>Abierto</b> ahora</span><span><b>{posts.filter((post) => post.kind === "proposal").length}</b> propuestas</span></div><button onClick={() => setComposerOpen(true)}>Presentar una idea <Icon name="arrow" size={17}/></button></section>
          {trending.length > 0 && <section className={styles.sideCard}><div className={styles.sideTitle}><span>Temas en movimiento</span></div><div className={styles.topicCloud}>{trending.map(([tag, count]) => <button key={tag} onClick={() => setQuery(tag)}>#{tag} <small>{count}</small></button>)}</div></section>}
          <section className={styles.sideCard}><div className={styles.sideTitle}><span>Personas sugeridas</span></div><div className={styles.peopleList}>{suggestions.map((person, index) => <div key={person.id}><span className={`${styles.avatar} ${[styles.avatarViolet, styles.avatarBlue, styles.avatarGold][index % 3]}`}>{initials(person.name)}</span><span><b>{person.name}</b><small>{person.headline}</small></span><button className={person.followed ? styles.following : ""} onClick={() => void followPerson(person)}>{person.followed ? "Siguiendo" : "Seguir"}</button></div>)}</div></section>
          <div className={styles.freePlan}><Icon name="lock" size={16}/><span><b>Plan de inicio gratuito</b><small>Publicá, conectá y colaborá sin costo.</small></span></div>
        </aside>
      </div>

      <nav className={styles.mobileNav} aria-label="Navegación móvil">{navItems.map((item) => <button key={item.label} className={activeNav === item.label ? styles.mobileActive : ""} onClick={() => selectNav(item.label)}><Icon name={item.icon} size={20}/><span>{item.label}</span></button>)}<button className={styles.mobilePublish} onClick={() => setComposerOpen(true)} aria-label="Publicar"><Icon name="plus" size={22}/></button></nav>

      {composerOpen && <div className={styles.modalBackdrop} role="presentation" onMouseDown={() => !publishing && setComposerOpen(false)}><section className={styles.composerModal} role="dialog" aria-modal="true" aria-labelledby="composer-title" onMouseDown={(event) => event.stopPropagation()}><div className={styles.modalHeader}><div><span>NUEVA PUBLICACIÓN</span><h2 id="composer-title">Compartí conocimiento</h2></div><button disabled={publishing} onClick={() => setComposerOpen(false)} aria-label="Cerrar"><Icon name="close" size={20}/></button></div><form onSubmit={submitPost}><label>Tipo de publicación<select name="kind" defaultValue="research"><option value="research">Investigación</option><option value="question">Pregunta abierta</option><option value="proposal">Propuesta colaborativa</option></select></label><label>Título<input name="title" required minLength={8} maxLength={220} placeholder="Un título claro ayuda a encontrar colaboradores"/></label><label>Resumen<textarea name="abstract" required minLength={20} maxLength={10000} rows={5} placeholder="Contá qué investigaste, qué necesitás o qué proponés…"/></label><div className={styles.modalGrid}><label>Comunidad<select name="community_id" defaultValue=""><option value="">Feed general</option>{communities.map((community) => <option key={community.id} value={community.id}>{community.name}</option>)}</select></label><label>Etiquetas<input name="tags" placeholder="agua, biodiversidad, datos"/></label></div><label className={styles.fileField}><Icon name="file" size={18}/><span><b>Adjuntar investigación</b><small>PDF, DOCX, CSV o imagen · máximo 15 MB</small></span><input name="attachment" type="file" accept=".pdf,.doc,.docx,.csv,.png,.jpg,.jpeg,.webp"/></label><div className={styles.modalFooter}><span><Icon name="lock" size={14}/>Visible para toda la comunidad</span><div><button type="button" disabled={publishing} onClick={() => setComposerOpen(false)}>Cancelar</button><button type="submit" disabled={publishing}>{publishing ? "Publicando…" : "Publicar ahora"}</button></div></div></form></section></div>}
      {notice && <div className={styles.toast}><span><Icon name="check" size={17}/></span>{notice}</div>}
    </div>
  );
}