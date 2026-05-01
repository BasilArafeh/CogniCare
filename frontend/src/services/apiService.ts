import axios, { AxiosInstance } from 'axios';
import * as FileSystem from 'expo-file-system/legacy';

const BASE_URL = 'http://localhost:8000';

export class ApiException extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = 'ApiException';
  }
}

// ─── Payload shape ────────────────────────────────────────────────────────────

export interface CaregiverData {
  name?: string;
  email?: string;
  phone?: string;
  password?: string;
  confirmPassword?: string;
}

export interface PatientData {
  firstName?: string;
  lastName?: string;
  username?: string;
  pin?: string;
  contactNo?: string;
  gender?: string;
  diagnosisStage?: string;
  dob?: string;
  address?: string;
  medicalNotes?: string;
  allergies?: string;
}

export interface MedicationEntry {
  id: string;
  name?: string;
  dosage?: string;
  time?: string;
  notes?: string;
}

export interface MealEntry {
  id: string;
  mealName?: string;
  mealTime?: string;
  notes?: string;
}

export interface ActivityEntry {
  id: string;
  name?: string;
  startTime?: string;
  endTime?: string;
  description?: string;
}

export interface FamilyMemberEntry {
  id: string;
  firstName?: string;
  lastName?: string;
  relationship?: string;
  contactNo?: string;
}

export interface EmergencyContactEntry {
  id: string;
  name?: string;
  phone?: string;
  relationship?: string;
  priority?: string;
}

export interface SetupPayload {
  caregiver: Record<string, unknown>;
  patient: Record<string, unknown>;
  medications: Record<string, unknown>[];
  meals: Record<string, unknown>[];
  activities: Record<string, unknown>[];
  family_members: Record<string, unknown>[];
  emergency_contacts: Record<string, unknown>[];
}

export function buildPayload(
  caregiverData: CaregiverData,
  patientData: PatientData,
  medications: MedicationEntry[],
  meals: MealEntry[],
  activities: ActivityEntry[],
  familyMembers: FamilyMemberEntry[],
  emergencyContacts: EmergencyContactEntry[],
): SetupPayload {
  const patientName = [patientData.firstName ?? '', patientData.lastName ?? '']
    .filter(Boolean)
    .join(' ');

  return {
    caregiver: {
      name: caregiverData.name ?? '',
      email: caregiverData.email ?? '',
      phone: caregiverData.phone ?? '',
      password: caregiverData.password ?? '',
    },
    patient: {
      name: patientName,
      username: patientData.username ?? '',
      pin: patientData.pin ?? '',
      gender: patientData.gender ?? '',
      phone: patientData.contactNo ?? '',
      diagnosis_stage: patientData.diagnosisStage ?? '',
      dob: patientData.dob ?? '',
      address: patientData.address ?? '',
      medical_notes: patientData.medicalNotes ?? '',
      allergies: patientData.allergies ?? '',
    },
    medications: medications.map((m) => ({
      name: m.name ?? '',
      dosage: m.dosage ?? '',
      time: m.time ?? '',
      notes: m.notes ?? '',
    })),
    meals: meals.map((m) => ({
      meal_name: m.mealName ?? '',
      meal_time: m.mealTime ?? '',
      notes: m.notes ?? '',
    })),
    activities: activities.map((a) => ({
      name: a.name ?? '',
      start_time: a.startTime ?? '',
      end_time: a.endTime ?? '',
      description: a.description ?? '',
    })),
    family_members: familyMembers.map((f) => ({
      name: [f.firstName ?? '', f.lastName ?? ''].filter(Boolean).join(' '),
      relationship: f.relationship ?? '',
      phone: f.contactNo ?? '',
    })),
    emergency_contacts: emergencyContacts.map((e) => ({
      name: e.name ?? '',
      phone: e.phone ?? '',
      relationship: e.relationship ?? '',
      priority: e.priority ?? '',
    })),
  };
}

// ─── API Service ──────────────────────────────────────────────────────────────

class ApiService {
  private readonly client: AxiosInstance;

  constructor(baseURL: string = BASE_URL) {
    this.client = axios.create({
      baseURL,
      timeout: 30_000,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  async postSetup(payload: SetupPayload): Promise<unknown> {
    try {
      const response = await this.client.post('/setup', payload);
      return response.data;
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        throw new ApiException(
          err.message,
          err.response?.status,
          err.response?.data,
        );
      }
      throw new ApiException(String(err));
    }
  }

  /**
   * Upload a recorded audio file and return a URI to the response audio.
   * The server returns audio bytes; we save them to a temp file and return the URI.
   */
  async postVoice(patientId: string, audioUri: string): Promise<string> {
    try {
      const formData = new FormData();
      formData.append('audio', {
        uri: audioUri,
        type: 'audio/m4a',
        name: 'voice.m4a',
      } as unknown as Blob);

      const response = await this.client.post(
        `/patients/${patientId}/voice`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          responseType: 'arraybuffer',
        },
      );

      const tempUri = `${FileSystem.cacheDirectory}cognicare_response_${Date.now()}.mp3`;
      const bytes: ArrayBuffer = response.data as ArrayBuffer;
      const base64 = arrayBufferToBase64(bytes);
      await FileSystem.writeAsStringAsync(tempUri, base64, {
        encoding: FileSystem.EncodingType.Base64,
      });

      return tempUri;
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        throw new ApiException(
          err.message,
          err.response?.status,
          err.response?.data,
        );
      }
      throw new ApiException(String(err));
    }
  }
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export const apiService = new ApiService();
export default apiService;
