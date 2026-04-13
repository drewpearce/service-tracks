/**
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 */

export interface User {
  id: string;
  email: string;
  email_verified: boolean;
  church_id: string;
  role: string;
}

export interface Church {
  id: string;
  name: string;
  slug: string;
}

export interface MeResponse {
  user: User;
  church: Church;
}

export interface LoginResponse {
  message: string;
}

export interface RegisterResponse {
  message: string;
}

export interface ServiceType {
  id: string;
  name: string;
}

export interface PcoConnectResponse {
  status: string;
  service_types: ServiceType[];
}

export interface SelectServiceTypeResponse {
  service_type_id: string;
  service_type_name: string;
}

export interface PcoStatusResponse {
  connected: boolean;
  auth_method: string | null;
  status: string | null;
  last_successful_call_at: string | null;
  service_type_id: string | null;
  service_type_name: string | null;
}

export interface StreamingConnectionStatus {
  platform: string;
  connected: boolean;
  status: string;
  external_user_id: string;
}

export interface StreamingStatusResponse {
  connections: StreamingConnectionStatus[];
}

export interface SpotifyAuthorizeResponse {
  authorization_url: string;
}

export interface YouTubeAuthorizeResponse {
  authorization_url: string;
}

export interface UnmatchedSong {
  pco_song_id: string;
  title: string;
  artist: string | null;
  last_used_date: string | null;
}

export interface UnmatchedSongsResponse {
  unmatched_songs: UnmatchedSong[];
}

export interface TrackSearchResult {
  track_id: string;
  title: string;
  artist: string | null;
  album: string | null;
  image_url: string | null;
  duration_ms: number | null;
}

export interface SearchResponse {
  results: TrackSearchResult[];
}

export interface MatchRequest {
  pco_song_id: string;
  pco_song_title: string;
  pco_song_artist: string | null;
  platform: string;
  track_id: string;
  track_title: string;
  track_artist: string | null;
}

export interface MatchResponse {
  message: string;
}

export interface SongMapping {
  id: string;
  pco_song_id: string;
  pco_song_title: string;
  pco_song_artist: string | null;
  platform: string;
  track_id: string;
  track_title: string;
  track_artist: string | null;
  created_at: string;
}

export interface MappingsResponse {
  mappings: SongMapping[];
}

export interface PlanSong {
  pco_song_id: string;
  title: string;
  matched: boolean;
}

export interface PlanPlaylist {
  platform: string;
  status: string;
  url: string | null;
  last_synced_at: string | null;
  error_message?: string | null;
}

export interface Plan {
  pco_plan_id: string;
  date: string;
  title: string;
  songs: PlanSong[];
  playlists: PlanPlaylist[];
  unmatched_count: number;
}

export interface PlansResponse {
  plans: Plan[];
}

export interface PlatformSyncResult {
  platform: string;
  sync_status: string;
  playlist_url: string | null;
  error_message: string | null;
}

export interface SyncTriggerResponse {
  sync_status: string;
  songs_total: number;
  songs_matched: number;
  songs_unmatched: number;
  platforms: PlatformSyncResult[];
}

export interface SyncLogEntry {
  id: string;
  sync_trigger: string;
  status: string;
  songs_total: number;
  songs_matched: number;
  songs_unmatched: number;
  started_at: string;
  completed_at: string | null;
}

export interface DashboardResponse {
  church_name: string;
  pco_connected: boolean;
  service_type_selected: boolean;
  streaming_connections: StreamingConnectionStatus[];
  upcoming_plans: Plan[];
  unmatched_song_count: number;
  recent_syncs: SyncLogEntry[];
}

export interface ChurchSettings {
  playlist_mode: "shared" | "per_plan";
  playlist_name_template: string;
  playlist_description_template: string;
}
