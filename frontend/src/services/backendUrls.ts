/**
 * Resolved base URLs for two CogniCare HTTP backends:
 * - RAG / general API: EXPO_PUBLIC_RAG_URL
 * - Speech + agent conversational routes tied to ai_agent deploy: EXPO_PUBLIC_AI_AGENT_URL
 */

import Constants from 'expo-constants';
import { Platform } from 'react-native';

function stripTrailingSlash(u: string): string {
  return u.replace(/\/$/, '');
}

/** LAN / simulator base when Expo provides a debugger host (default port configurable). */
export function resolveExpoDevBackendBaseUrl(port: number): string {
  const constantsAny = Constants as unknown as {
    expoConfig?: { hostUri?: string };
    manifest?: { debuggerHost?: string };
    manifest2?: { extra?: { expoGo?: { debuggerHost?: string } } };
  };
  const hostUri =
    constantsAny.expoConfig?.hostUri ??
    constantsAny.manifest2?.extra?.expoGo?.debuggerHost ??
    constantsAny.manifest?.debuggerHost ??
    null;
  const host = hostUri?.split(':')[0] ?? null;
  if (host) return `http://${host}:${port}`;
  if (Platform.OS === 'android') return `http://10.0.2.2:${port}`;
  return `http://localhost:${port}`;
}

/** General RAG / non-speech CogniCare API (default dev port 8000). */
export function getRagBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_RAG_URL?.trim();
  if (configured) return stripTrailingSlash(configured);
  return resolveExpoDevBackendBaseUrl(8000);
}

/**
 * CogniCare ai_agent deploy: speech (STT/TTS/voice) and optionally other agent routes
 * live here only (default dev port 8001 when unset — set env if your agent shares RAG port).
 */
export function getAiAgentBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_AI_AGENT_URL?.trim();
  if (configured) return stripTrailingSlash(configured);
  return resolveExpoDevBackendBaseUrl(8001);
}
