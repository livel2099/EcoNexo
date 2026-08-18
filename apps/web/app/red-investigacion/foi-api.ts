import { API, apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "../lib/api";

export type FoiPostKind = "research" | "question" | "proposal";

export interface FoiAuthor {
  id: string;
  name: string;
  headline: string;
  institution: string | null;
  discipline: string | null;
  avatar_url: string | null;
  followed: boolean;
}

export interface FoiCommunity {
  id: string;
  slug: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  members_count: number;
  posts_count: number;
  joined: boolean;
}

export interface FoiPost {
  id: string;
  kind: FoiPostKind;
  title: string;
  abstract: string;
  tags: string[];
  attachment_url: string | null;
  attachment_name: string | null;
  attachment_mime: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  author: FoiAuthor;
  community: FoiCommunity | null;
  likes_count: number;
  comments_count: number;
  liked: boolean;
  saved: boolean;
}

export interface FoiComment {
  id: string;
  body: string;
  created_at: string;
  updated_at: string;
  author: FoiAuthor;
}

export interface FoiProfile extends FoiAuthor {
  email: string | null;
  bio: string | null;
  location: string | null;
  website: string | null;
  orcid: string | null;
  interests: string[];
  followers_count: number;
  following_count: number;
  posts_count: number;
}

export interface FoiPostInput {
  kind: FoiPostKind;
  title: string;
  abstract: string;
  tags: string[];
  community_id?: string;
  attachment_url?: string;
  attachment_name?: string;
  attachment_mime?: string;
}

export interface FoiUpload {
  url: string;
  name: string;
  mime: string;
  size: number;
}

export async function fetchFoiPosts(token: string, options: {
  q?: string;
  kind?: FoiPostKind;
  communityId?: string;
  scope?: "all" | "following" | "saved";
} = {}): Promise<FoiPost[]> {
  const params = new URLSearchParams();
  if (options.q) params.set("q", options.q);
  if (options.kind) params.set("kind", options.kind);
  if (options.communityId) params.set("community_id", options.communityId);
  if (options.scope && options.scope !== "all") params.set("scope", options.scope);
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiGet<FoiPost[]>(`/foi/posts${suffix}`, token);
}

export const fetchFoiCommunities = (token: string) => apiGet<FoiCommunity[]>("/foi/communities", token);
export const fetchFoiSuggestions = (token: string) => apiGet<FoiAuthor[]>("/foi/profiles/suggested", token);
export const fetchFoiProfile = (token: string) => apiGet<FoiProfile>("/foi/profile/me", token);
export const createFoiPost = (token: string, body: FoiPostInput) => apiPost<FoiPost>("/foi/posts", token, body);
export const deleteFoiPost = (token: string, postId: string) => apiDelete(`/foi/posts/${postId}`, token);
export const toggleFoiLike = (token: string, postId: string) => apiPost<{ active: boolean; count: number }>(`/foi/posts/${postId}/like`, token, {});
export const toggleFoiSave = (token: string, postId: string) => apiPost<{ active: boolean; count: number }>(`/foi/posts/${postId}/save`, token, {});
export const fetchFoiComments = (token: string, postId: string) => apiGet<FoiComment[]>(`/foi/posts/${postId}/comments`, token);
export const createFoiComment = (token: string, postId: string, body: string) => apiPost<FoiComment>(`/foi/posts/${postId}/comments`, token, { body });
export const toggleFoiCommunity = (token: string, communityId: string) => apiPost<{ active: boolean; count: number }>(`/foi/communities/${communityId}/join`, token, {});
export const toggleFoiFollow = (token: string, profileId: string) => apiPost<{ active: boolean; count: number }>(`/foi/profiles/${profileId}/follow`, token, {});
export const updateFoiProfile = (token: string, body: Partial<FoiProfile>) => apiPatch<FoiProfile>("/foi/profile/me", token, body);

export async function uploadFoiFile(token: string, file: File): Promise<FoiUpload> {
  const form = new FormData();
  form.append("file", file);
  return apiPostForm<FoiUpload>("/foi/uploads", token, form);
}
export async function downloadFoiFile(token: string, url: string, filename: string): Promise<void> {
  const target = new URL(url, API);
  if (target.origin !== new URL(API).origin) {
    window.open(target.toString(), "_blank", "noopener,noreferrer");
    return;
  }
  const response = await fetch(target, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(response.status === 401 ? "Tu sesión venció. Volvé a ingresar." : "No se pudo descargar el archivo");
  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename || "investigacion";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}