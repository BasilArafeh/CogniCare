import axios, { AxiosInstance } from 'axios';
import * as FileSystem from 'expo-file-system/legacy';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { supabase } from './supabaseClient';

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '';

function resolveAiAgentBaseUrl(): string {
  // Explicit env var wins (supports both old and clearer naming).
  const configured =
    process.env.EXPO_PUBLIC_AI_AGENT_URL?.trim() ||
    process.env.EXPO_PUBLIC_RAG_URL?.trim();
  if (configured) return configured;

  // Expo host info can be present in multiple places depending on SDK/runtime.
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
  // Example hostUri/debuggerHost: "192.168.1.14:8081" -> "http://192.168.1.14:8000"
  const host = hostUri?.split(':')[0] ?? null;
  if (host) return `http://${host}:8000`;

  // Android emulator needs the special loopback alias.
  if (Platform.OS === 'android') return 'http://10.0.2.2:8000';

  // iOS simulator on same machine can still use localhost.
  return 'http://localhost:8000';
}

const RAG_BASE_URL = resolveAiAgentBaseUrl();
console.log('[API] AI agent base URL =', RAG_BASE_URL);

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

// ─── Payload shapes ───────────────────────────────────────────────────────────

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
  return {
    caregiver: {
      name: caregiverData.name ?? '',
      email: caregiverData.email ?? '',
      phone: caregiverData.phone ?? '',
      password: caregiverData.password ?? '',
    },
    patient: {
      first_name: patientData.firstName ?? '',
      last_name: patientData.lastName ?? '',
      username: patientData.username ?? '',
      pin: patientData.pin ?? '',
      gender: patientData.gender ?? '',
      contact_no: patientData.contactNo ?? '',
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
    })),
    activities: activities.map((a) => ({
      name: a.name ?? '',
      start_time: a.startTime ?? '',
      end_time: a.endTime ?? '',
      description: a.description ?? '',
    })),
    family_members: familyMembers.map((f) => ({
      first_name: f.firstName ?? '',
      last_name: f.lastName ?? '',
      relationship: f.relationship ?? '',
      contact_no: f.contactNo ?? '',
    })),
    emergency_contacts: emergencyContacts.map((e) => ({
      name: e.name ?? '',
      phone: e.phone ?? '',
      relationship: e.relationship ?? '',
      priority: e.priority ?? '',
    })),
  };
}

// ─── Dashboard display types ──────────────────────────────────────────────────

export interface PatientRow {
  patient_id: number;
  first_name: string;
  last_name: string;
  gender: string | null;
  dob: string | null;
  address: string | null;
  contact_no: string | null;
  diagnosis_stage: string;
  emergency_contact: string | null;
}

interface PatientMedRow {
  patient_medications_id: number;
  medication_id: number;
  patient_id: number;
  medication_time: string;
  dosage: string | null;
  medication: { medication_id: number; medication_name: string; medication_description: string | null } | null;
}

interface PatientMealRow {
  patient_meal_id: number;
  meal_id: number;
  patient_id: number;
  meal_time: string;
  meals: { meal_id: number; meal_type: string } | null;
}

interface PatientActivityRow {
  patient_activity_id: number;
  activity_id: number;
  patient_id: number;
  start_time: string;
  end_time: string | null;
  description: string | null;
  activity: { activity_id: number; activity_type: string } | null;
}

interface FamilyRow {
  family_member_id: number;
  patient_id: number;
  first_name: string;
  last_name: string;
  relationship: string | null;
  contact_no: string | null;
}

export interface MedDisplay {
  patientMedicationId: number;
  medicationId: number;
  name: string;
  dosage: string | null;
  time: string;
  notes: string | null;
}

export interface MealDisplay {
  patientMealId: number;
  mealId: number;
  mealType: string;
  mealTime: string;
}

export interface ActivityDisplay {
  patientActivityId: number;
  activityId: number;
  name: string;
  startTime: string;
  endTime: string | null;
  description: string | null;
}

export interface FamilyDisplay {
  familyMemberId: number;
  firstName: string;
  lastName: string;
  relationship: string | null;
  contactNo: string | null;
}

interface CaregiverPriorityRow {
  caregiver_priority_id: number;
  patient_id: number;
  caregiver_id: number;
  priority_level: number;
  contact_method: string | null;
  caregiver: {
    caregiver_id: number;
    first_name: string;
    last_name: string;
    contact_no: string | null;
    role: string | null;
  } | null;
}

export interface EmergencyContactDisplay {
  caregiverPriorityId: number;
  caregiverId: number;
  name: string;
  phone: string | null;
  relationship: string | null;
  priorityLevel: number;
}

interface ReportRow {
  report_id: number;
  caregiver_id: number;
  report_date: string;
  description: string | Record<string, unknown> | null;
}

export interface WeeklyReportDisplay {
  reportId: number;
  caregiverId: number;
  reportDate: string;
  title: string;
  period: string;
  pdfUrl: string;
}



// PIN is 4 digits; Supabase requires passwords >= 6 chars.
// Applied identically on signup and login so they always match.
function pinToPassword(pin: string): string {
  return `${pin}${pin}`;
}

// ─── API Service ──────────────────────────────────────────────────────────────

class ApiService {
  private readonly db: AxiosInstance;
  private readonly rag: AxiosInstance;

  constructor() {
    this.db = axios.create({
      baseURL: `${SUPABASE_URL}/rest/v1`,
      timeout: 30_000,
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        'Content-Type': 'application/json',
        Prefer: 'return=representation',
      },
    });

    // Python RAG backend — no auth headers needed
    this.rag = axios.create({
      baseURL: RAG_BASE_URL,
      timeout: 60_000,
    });
  }

  // ─── RAG Backend ─────────────────────────────────────────────────────────
  //
  // Expected backend endpoints:
  //
  //   GET  /health
  //        → 200 { status: "ok" }
  //
  //   POST /agent/chat
  //        Body: { patient_id: string, message: string, language: string }
  //        → 200 { response: string, patient_id: string }
  //
  //   POST /voice
  //        Body: multipart/form-data  { patient_id: number, audio: File (WAV) }
  //        → 200 { transcript: string, reply_text: string, audio_url: string }
  //               audio_url is a full URL this server serves (GET returns WAV bytes)
  //
  //   POST /reports/generate/{patient_id}
  //        → triggers report generation; result appears in weekly_report table

  async pingBackend(): Promise<boolean> {
    try {
      const { data } = await this.rag.get<{ status: string }>('/health', { timeout: 5_000 });
      return data.status === 'ok';
    } catch {
      return false;
    }
  }

  async sendChatMessage(patientId: number, message: string, language = 'en'): Promise<string> {
    const url = `${RAG_BASE_URL}/agent/chat`;
    console.log('[API] sendChatMessage: hitting', url, '| patient_id =', patientId, '| language =', language, '| message =', message);
    try {
      const { data } = await this.rag.post<{ response: string }>('/agent/chat', {
        patient_id: String(patientId),
        message,
        language,
      });
      console.log('[API] sendChatMessage: reply =', data.response);
      return data.response;
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        console.error('[API] sendChatMessage FAILED | url =', url, '| status =', err.response?.status ?? 'no response', '| code =', err.code, '| message =', err.message, '| body =', JSON.stringify(err.response?.data));
      } else {
        console.error('[API] sendChatMessage FAILED | unexpected error =', err);
      }
      throw err;
    }
  }

  async sendVoiceRecording(
    patientId: number,
    audioUri: string,
  ): Promise<{ transcript: string; replyText: string; audioUri: string }> {
    const form = new FormData();
    form.append('patient_id', String(patientId));
    form.append('audio', { uri: audioUri, name: 'recording.wav', type: 'audio/wav' } as unknown as Blob);

    const { data } = await this.rag.post<{
      transcript: string;
      reply_text: string;
      audio_url:  string;
    }>('/voice', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
    });

    // Download the response WAV to local storage so expo-av can play it
    const destUri = `${FileSystem.documentDirectory}response_${patientId}_${Date.now()}.wav`;
    await FileSystem.downloadAsync(data.audio_url, destUri);

    return {
      transcript: data.transcript,
      replyText:  data.reply_text,
      audioUri:   destUri,
    };
  }

  // ─── Lookup-table helpers (find or create) ────────────────────────────────
  // Meals, activities, and medications are shared lookup tables.
  // Always reuse an existing row before inserting a new one.

  private async findOrCreateMealId(mealType: string): Promise<number> {
    const name = normalizeLabel(mealType);
    const { data } = await this.db.get<Array<{ meal_id: number }>>(
      `/meals?meal_type=ilike.${encodeURIComponent(name)}&select=meal_id`,
    );
    if (data[0]) return data[0].meal_id;
    const { data: [created] } = await this.db.post<Array<{ meal_id: number }>>(
      '/meals', { meal_type: name },
    );
    return created.meal_id;
  }

  private async findOrCreateActivityId(activityType: string): Promise<number> {
    const name = normalizeLabel(activityType);
    const { data } = await this.db.get<Array<{ activity_id: number }>>(
      `/activity?activity_type=ilike.${encodeURIComponent(name)}&select=activity_id`,
    );
    if (data[0]) return data[0].activity_id;
    const { data: [created] } = await this.db.post<Array<{ activity_id: number }>>(
      '/activity', { activity_type: name },
    );
    return created.activity_id;
  }

  private async findOrCreateMedicationId(medicationName: string, notes: string): Promise<number> {
    const name = normalizeLabel(medicationName);
    const { data } = await this.db.get<Array<{ medication_id: number }>>(
      `/medication?medication_name=ilike.${encodeURIComponent(name)}&select=medication_id`,
    );
    if (data[0]) return data[0].medication_id;
    const { data: [created] } = await this.db.post<Array<{ medication_id: number }>>(
      '/medication', { medication_name: name, medication_description: orNull(notes) },
    );
    return created.medication_id;
  }

  /**
   * Full onboarding insert into Supabase across 10+ tables.
   *
   * Insert order (respects FK dependencies):
   *   patients → caregiver → patient_memory → caregiver_priority
   *   → medication + patient_medications (per item)
   *   → meals + patient_meals (per item)
   *   → activity + patient_activities (per item)
   *   → family_member (batch)
   *   → caregiver + caregiver_priority for each emergency contact
   */
  async postSetup(payload: SetupPayload): Promise<{ patientId: number; caregiverId: number }> {
    console.log('[API] postSetup: starting onboarding setup');
    try {
      // ── 0. Create Supabase Auth users for caregiver + patient (non-fatal) ──────
      const authEmail = (payload.caregiver.email as string) ?? '';
      const authPassword = (payload.caregiver.password as string) ?? '';
      let authUserId: string | null = null;
      if (authEmail && authPassword) {
        console.log('[API] postSetup: creating caregiver auth user for', authEmail);
        const { data: authData, error: authError } = await supabase.auth.signUp({
          email: authEmail,
          password: authPassword,
        });
        if (authError) {
          console.error('[API] postSetup: caregiver auth signup failed —', authError.message);
          throw new ApiException(`Caregiver sign-up failed: ${authError.message}`);
        }
        if (authData.user) {
          authUserId = authData.user.id;
          console.log('[API] postSetup: caregiver auth user created, id =', authUserId);
        }
      }

      const patientUsername = (payload.patient.username as string) ?? '';
      const patientPin = (payload.patient.pin as string) ?? '';
      let patientAuthUserId: string | null = null;
      if (patientUsername && patientPin) {
        const patientEmail = `pt_${patientUsername.toLowerCase()}@example.com`;
        console.log('[API] postSetup: creating patient auth user for', patientEmail);
        const { data: patientAuthData, error: patientAuthError } = await supabase.auth.signUp({
          email: patientEmail,
          password: pinToPassword(patientPin),
        });
        if (patientAuthError) {
          console.warn('[API] postSetup: patient auth signup failed —', patientAuthError.message);
        } else if (patientAuthData.user) {
          patientAuthUserId = patientAuthData.user.id;
          console.log('[API] postSetup: patient auth user created, id =', patientAuthUserId);
        }
      }

      // ── 1. patients ─────────────────────────────────────────────────────────
      // last_name and diagnosis_stage are NOT NULL in schema — send '' if empty
      const primaryEmergency = payload.emergency_contacts[0];
      const emergencyContactText = primaryEmergency
        ? (primaryEmergency.phone as string) || null
        : null;

      console.log('[API] postSetup: inserting patient row');
      const { data: patientsRows } = await this.db.post<Array<{ patient_id: number }>>(
        '/patients',
        {
          first_name: payload.patient.first_name,
          last_name: (payload.patient.last_name as string) || '',
          auth_user_id: patientAuthUserId,
          gender: orNull(payload.patient.gender),
          dob: orNull(payload.patient.dob),
          address: orNull(payload.patient.address),
          contact_no: orNull(payload.patient.contact_no),
          diagnosis_stage: (payload.patient.diagnosis_stage as string) || '',
          emergency_contact: emergencyContactText,
        },
      );
      const patientId = patientsRows[0].patient_id;
      console.log('[API] postSetup: patient inserted, patient_id =', patientId);

      // ── 2. caregiver (primary) ───────────────────────────────────────────────
      // last_name is NOT NULL — use '' if single-word name.
      // contact_no has CHECK (must be E.164 format "+XXXXXXXXXXX") — use e164OrNull.
      const caregiverName = (payload.caregiver.name as string) ?? '';
      const [cgFirst, ...cgRest] = caregiverName.split(' ');

      console.log('[API] postSetup: inserting caregiver row');
      const { data: caregiverRows } = await this.db.post<Array<{ caregiver_id: number }>>(
        '/caregiver',
        {
          patient_id: patientId,
          first_name: cgFirst || caregiverName || '',
          last_name: cgRest.length > 0 ? cgRest.join(' ') : '',
          contact_no: e164OrNull(payload.caregiver.phone),
          role: 'Primary Caregiver',
          auth_user_id: authUserId,
        },
      );
      const caregiverId = caregiverRows[0].caregiver_id;
      console.log('[API] postSetup: caregiver inserted, caregiver_id =', caregiverId);

      // ── 3. patient_memory ────────────────────────────────────────────────────
      // confusion_patterns and important_people default to [] in schema (not {}).
      // communication_profile NOT NULL — send schema default.
      // created_at / updated_at have DB defaults — omit them.
      const allergiesRaw = (payload.patient.allergies as string) ?? '';
      console.log('[API] postSetup: inserting patient_memory');
      await this.db.post('/patient_memory', {
        patient_id: patientId,
        communication_profile: {
          pace: 'slow',
          tone: 'reassuring',
          sentence_length: 'short',
          repeat_if_confused: true,
        },
        confusion_patterns: [],
        important_people: [],
        primary_caregiver_id: caregiverId,
        dietary_notes: orNull(payload.patient.medical_notes),
        allergies: allergiesRaw
          ? allergiesRaw.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
      });
      console.log('[API] postSetup: patient_memory inserted');

      // ── 4. caregiver_priority (primary caregiver = level 1) ─────────────────
      console.log('[API] postSetup: inserting caregiver_priority (level 1)');
      await this.db.post('/caregiver_priority', {
        patient_id: patientId,
        caregiver_id: caregiverId,
        priority_level: 1,
        contact_method: orNull(payload.caregiver.phone),
      });
      console.log('[API] postSetup: caregiver_priority inserted');

      // ── 5. medications ───────────────────────────────────────────────────────
      console.log('[API] postSetup: inserting', payload.medications.length, 'medication(s)');
      for (const med of payload.medications) {
        const medicationId = await this.findOrCreateMedicationId(
          med.name as string, med.notes as string,
        );
        await this.db.post('/patient_medications', {
          medication_id: medicationId,
          patient_id: patientId,
          medication_time: toTime(med.time as string) ?? '00:00:00',
          dosage: orNull(med.dosage),
        });
        console.log('[API] postSetup: medication linked —', med.name, 'id =', medicationId);
      }

      // ── 6. meals ─────────────────────────────────────────────────────────────
      console.log('[API] postSetup: inserting', payload.meals.length, 'meal(s)');
      for (const meal of payload.meals) {
        const mealId = await this.findOrCreateMealId(meal.meal_name as string);
        await this.db.post('/patient_meals', {
          meal_id: mealId,
          patient_id: patientId,
          meal_time: toTime(meal.meal_time as string) ?? '00:00:00',
        });
        console.log('[API] postSetup: meal linked —', meal.meal_name, 'id =', mealId);
      }

      // ── 7. activities ─────────────────────────────────────────────────────────
      console.log('[API] postSetup: inserting', payload.activities.length, 'activity/activities');
      for (const act of payload.activities) {
        const activityId = await this.findOrCreateActivityId(act.name as string);
        await this.db.post('/patient_activities', {
          activity_id: activityId,
          patient_id: patientId,
          start_time: toTime(act.start_time as string) ?? '00:00:00',
          end_time: toTime(act.end_time as string),
          description: orNull(act.description),
        });
        console.log('[API] postSetup: activity linked —', act.name, 'id =', activityId);
      }

      // ── 8. family_member (batch) ──────────────────────────────────────────────
      // last_name is NOT NULL — use '' if empty. contact_no has no format constraint.
      console.log('[API] postSetup: inserting', payload.family_members.length, 'family member(s)');
      if (payload.family_members.length > 0) {
        await this.db.post(
          '/family_member',
          payload.family_members.map((f) => ({
            patient_id: patientId,
            first_name: f.first_name,
            last_name: (f.last_name as string) || '',
            relationship: orNull(f.relationship),
            contact_no: orNull(f.contactNo),
          })),
        );
        console.log('[API] postSetup: family members inserted');
      }

      // ── 9. emergency contacts → caregiver + caregiver_priority ───────────────
      // Stored as caregivers; primary occupies level 1, emergency contacts start at 2.
      // last_name NOT NULL; contact_no must be E.164 or null (same CHECK as caregiver).
      const priorityMap: Record<string, number> = { Primary: 2, Secondary: 3, Backup: 4 };

      console.log('[API] postSetup: inserting', payload.emergency_contacts.length, 'emergency contact(s)');
      for (const contact of payload.emergency_contacts) {
        const contactName = (contact.name as string) ?? '';
        const [ecFirst, ...ecRest] = contactName.split(' ');

        const { data: [ecRow] } = await this.db.post<Array<{ caregiver_id: number }>>(
          '/caregiver',
          {
            patient_id: patientId,
            first_name: ecFirst || contactName || '',
            last_name: ecRest.length > 0 ? ecRest.join(' ') : '',
            contact_no: e164OrNull(contact.phone),
            role: orNull(contact.relationship),
          },
        );
        await this.db.post('/caregiver_priority', {
          patient_id: patientId,
          caregiver_id: ecRow.caregiver_id,
          priority_level: priorityMap[contact.priority as string] ?? 5,
          contact_method: orNull(contact.phone),
        });
        console.log('[API] postSetup: emergency contact inserted —', contactName, 'caregiver_id =', ecRow.caregiver_id);
      }

      console.log('[API] postSetup: done — patient_id =', patientId, '| caregiver_id =', caregiverId);
      return { patientId, caregiverId };
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        console.error('[API] postSetup: failed —', err.message, '| status =', err.response?.status, '| body =', JSON.stringify(err.response?.data));
        throw new ApiException(err.message, err.response?.status, err.response?.data);
      }
      console.error('[API] postSetup: unexpected error —', err);
      throw new ApiException(String(err));
    }
  }

  // ─── Dashboard GET ────────────────────────────────────────────────────────

  async getPatient(patientId: number): Promise<PatientRow | null> {
    try {
      const { data } = await this.db.get<PatientRow[]>(
        `/patients?patient_id=eq.${patientId}&select=*`,
      );
      return data[0] ?? null;
    } catch { return null; }
  }

  async editPatient(patientId: number, updates: {
    firstName?: string;
    lastName?: string;
    gender?: string;
    dob?: string;
    address?: string;
    contactNo?: string;
    diagnosisStage?: string;
  }): Promise<void> {
    const body: Record<string, unknown> = {};
    if (updates.firstName !== undefined) body.first_name = updates.firstName;
    if (updates.lastName !== undefined) body.last_name = updates.lastName || '';
    if (updates.gender !== undefined) body.gender = orNull(updates.gender);
    if (updates.dob !== undefined) body.dob = orNull(updates.dob);
    if (updates.address !== undefined) body.address = orNull(updates.address);
    if (updates.contactNo !== undefined) body.contact_no = orNull(updates.contactNo);
    if (updates.diagnosisStage !== undefined) body.diagnosis_stage = updates.diagnosisStage;
    await this.db.patch(`/patients?patient_id=eq.${patientId}`, body);
  }

  async getPatientMedications(patientId: number): Promise<MedDisplay[]> {
    try {
      const { data } = await this.db.get<PatientMedRow[]>(
        `/patient_medications?patient_id=eq.${patientId}&select=*,medication(*)`,
      );
      return data.map((r) => ({
        patientMedicationId: r.patient_medications_id,
        medicationId: r.medication_id,
        name: r.medication?.medication_name ?? '',
        dosage: r.dosage ?? null,
        time: r.medication_time ?? '',
        notes: r.medication?.medication_description ?? null,
      }));
    } catch { return []; }
  }

  async getPatientMeals(patientId: number): Promise<MealDisplay[]> {
    try {
      const { data } = await this.db.get<PatientMealRow[]>(
        `/patient_meals?patient_id=eq.${patientId}&select=*,meals(*)`,
      );
      return data.map((r) => ({
        patientMealId: r.patient_meal_id,
        mealId: r.meal_id,
        mealType: r.meals?.meal_type ?? '',
        mealTime: r.meal_time ?? '',
      }));
    } catch { return []; }
  }

  async getPatientActivities(patientId: number): Promise<ActivityDisplay[]> {
    try {
      const { data } = await this.db.get<PatientActivityRow[]>(
        `/patient_activities?patient_id=eq.${patientId}&select=*,activity(*)`,
      );
      return data.map((r) => ({
        patientActivityId: r.patient_activity_id,
        activityId: r.activity_id,
        name: r.activity?.activity_type ?? '',
        startTime: r.start_time ?? '',
        endTime: r.end_time ?? null,
        description: r.description ?? null,
      }));
    } catch { return []; }
  }

  async getFamilyMembers(patientId: number): Promise<FamilyDisplay[]> {
    try {
      const { data } = await this.db.get<FamilyRow[]>(
        `/family_member?patient_id=eq.${patientId}&select=*`,
      );
      return data.map((r) => ({
        familyMemberId: r.family_member_id,
        firstName: r.first_name ?? '',
        lastName: r.last_name ?? '',
        relationship: r.relationship ?? null,
        contactNo: r.contact_no ?? null,
      }));
    } catch { return []; }
  }

  // ─── Dashboard ADD ────────────────────────────────────────────────────────

  async addMedication(
    patientId: number,
    name: string, dosage: string, time: string, notes: string,
  ): Promise<void> {
    const medicationId = await this.findOrCreateMedicationId(name, notes);
    await this.db.post('/patient_medications', {
      medication_id: medicationId,
      patient_id: patientId,
      medication_time: toTime(time) ?? '00:00:00',
      dosage: orNull(dosage),
    });
  }

  async addMeal(patientId: number, mealName: string, mealTime: string): Promise<void> {
    const mealId = await this.findOrCreateMealId(mealName);
    await this.db.post('/patient_meals', {
      meal_id: mealId,
      patient_id: patientId,
      meal_time: toTime(mealTime) ?? '00:00:00',
    });
  }

  async addActivity(
    patientId: number,
    name: string, startTime: string, endTime: string, description: string,
  ): Promise<void> {
    const activityId = await this.findOrCreateActivityId(name);
    await this.db.post('/patient_activities', {
      activity_id: activityId,
      patient_id: patientId,
      start_time: toTime(startTime) ?? '00:00:00',
      end_time: toTime(endTime),
      description: orNull(description),
    });
  }

  // ─── Dashboard DELETE ─────────────────────────────────────────────────────

  async deleteMedication(patientMedicationId: number, _medicationId: number): Promise<void> {
    await this.db.delete(`/patient_medications?patient_medications_id=eq.${patientMedicationId}`);
  }

  async deleteMeal(patientMealId: number, _mealId: number): Promise<void> {
    await this.db.delete(`/patient_meals?patient_meal_id=eq.${patientMealId}`);
  }

  async deleteActivity(patientActivityId: number, _activityId: number): Promise<void> {
    await this.db.delete(`/patient_activities?patient_activity_id=eq.${patientActivityId}`);
  }

  // ─── Dashboard EDIT ───────────────────────────────────────────────────────

  async editMedication(
    patientMedicationId: number, _medicationId: number,
    name: string, dosage: string, time: string, notes: string,
  ): Promise<void> {
    const medicationId = await this.findOrCreateMedicationId(name, notes);
    await this.db.patch(`/patient_medications?patient_medications_id=eq.${patientMedicationId}`, {
      medication_id: medicationId,
      medication_time: toTime(time) ?? '00:00:00',
      dosage: orNull(dosage),
    });
  }

  async editMeal(patientMealId: number, _mealId: number, mealName: string, mealTime: string): Promise<void> {
    const mealId = await this.findOrCreateMealId(mealName);
    await this.db.patch(`/patient_meals?patient_meal_id=eq.${patientMealId}`, {
      meal_id: mealId,
      meal_time: toTime(mealTime) ?? '00:00:00',
    });
  }

  async editActivity(
    patientActivityId: number, _activityId: number,
    name: string, startTime: string, endTime: string, description: string,
  ): Promise<void> {
    const activityId = await this.findOrCreateActivityId(name);
    await this.db.patch(`/patient_activities?patient_activity_id=eq.${patientActivityId}`, {
      activity_id: activityId,
      start_time: toTime(startTime) ?? '00:00:00',
      end_time: toTime(endTime),
      description: orNull(description),
    });
  }

  // ─── Family Members ───────────────────────────────────────────────────────

  async addFamilyMember(
    patientId: number, firstName: string, lastName: string,
    relationship: string, contactNo: string,
  ): Promise<void> {
    await this.db.post('/family_member', {
      patient_id: patientId,
      first_name: firstName,
      last_name: lastName || '',
      relationship: orNull(relationship),
      contact_no: orNull(contactNo),
    });
  }

  async editFamilyMember(
    familyMemberId: number, firstName: string, lastName: string,
    relationship: string, contactNo: string,
  ): Promise<void> {
    await this.db.patch(`/family_member?family_member_id=eq.${familyMemberId}`, {
      first_name: firstName,
      last_name: lastName || '',
      relationship: orNull(relationship),
      contact_no: orNull(contactNo),
    });
  }

  async deleteFamilyMember(familyMemberId: number): Promise<void> {
    await this.db.delete(`/family_member?family_member_id=eq.${familyMemberId}`);
  }

  // ─── Emergency Contacts ───────────────────────────────────────────────────

  async getEmergencyContacts(patientId: number): Promise<EmergencyContactDisplay[]> {
    try {
      const { data } = await this.db.get<CaregiverPriorityRow[]>(
        `/caregiver_priority?patient_id=eq.${patientId}&priority_level=gt.1&select=*,caregiver(*)`,
      );
      return data.map((r) => ({
        caregiverPriorityId: r.caregiver_priority_id,
        caregiverId: r.caregiver_id,
        name: [r.caregiver?.first_name, r.caregiver?.last_name].filter(Boolean).join(' ') || 'Unknown',
        phone: r.caregiver?.contact_no ?? null,
        relationship: r.caregiver?.role ?? null,
        priorityLevel: r.priority_level,
      }));
    } catch { return []; }
  }

  async addEmergencyContact(
    patientId: number, name: string, phone: string, relationship: string,
  ): Promise<void> {
    const parts = name.trim().split(' ');
    const { data: [cg] } = await this.db.post<Array<{ caregiver_id: number }>>('/caregiver', {
      patient_id: patientId,
      first_name: parts[0] || '',
      last_name: parts.slice(1).join(' ') || '',
      contact_no: e164OrNull(phone),
      role: orNull(relationship),
    });
    const { data: existing } = await this.db.get<Array<{ priority_level: number }>>(
      `/caregiver_priority?patient_id=eq.${patientId}&select=priority_level&order=priority_level.desc&limit=1`,
    );
    const nextPriority = (existing[0]?.priority_level ?? 1) + 1;
    await this.db.post('/caregiver_priority', {
      patient_id: patientId,
      caregiver_id: cg.caregiver_id,
      priority_level: nextPriority,
      contact_method: e164OrNull(phone),
    });
  }

  async editEmergencyContact(
    caregiverId: number, name: string, phone: string, relationship: string,
  ): Promise<void> {
    const parts = name.trim().split(' ');
    await this.db.patch(`/caregiver?caregiver_id=eq.${caregiverId}`, {
      first_name: parts[0] || '',
      last_name: parts.slice(1).join(' ') || '',
      contact_no: e164OrNull(phone),
      role: orNull(relationship),
    });
  }

  async deleteEmergencyContact(caregiverId: number, caregiverPriorityId: number): Promise<void> {
    await this.db.delete(`/caregiver_priority?caregiver_priority_id=eq.${caregiverPriorityId}`);
    await this.db.delete(`/caregiver?caregiver_id=eq.${caregiverId}`);
  }

  // ─── Weekly Reports ───────────────────────────────────────────────────────

  async getWeeklyReports(caregiverId: number, patientId: number): Promise<WeeklyReportDisplay[]> {
    try {
      const { data } = await this.db.get<ReportRow[]>(
        `/report?caregiver_id=eq.${caregiverId}&select=*&order=report_date.desc`,
      );
      console.log('[API] getWeeklyReports: raw rows =', JSON.stringify(data));
      return data.map((r) => {
        let title = 'Health Report';
        let period = '';
        try {
          const raw = r.description ?? '{}';
          const parsed: Record<string, unknown> =
            typeof raw === 'string' ? JSON.parse(raw) : (raw as Record<string, unknown>);
          title = (parsed.title as string) ?? title;
          period = (parsed.period as string) ?? '';
        } catch { /* use defaults */ }
        return {
          reportId: r.report_id,
          caregiverId: r.caregiver_id,
          reportDate: r.report_date,
          title,
          period,
          pdfUrl: `${RAG_BASE_URL}/reports/patient/${patientId}/pdf`,
        };
      });
    } catch (err) {
      console.error('[API] getWeeklyReports failed:', err);
      return [];
    }
  }

  getPdfUrl(patientId: number): string {
    return `${RAG_BASE_URL}/reports/patient/${patientId}/pdf`;
  }

  // ─── Auth ─────────────────────────────────────────────────────────────────

  async getCaregiverByAuthId(authUserId: string): Promise<{
    caregiverId: number; caregiverName: string; patientId: number; patientName: string;
  } | null> {
    type Row = Array<{
      caregiver_id: number; first_name: string; last_name: string;
      patient_id: number; patients: { first_name: string; last_name: string } | null;
    }>;
    try {
      const { data } = await this.db.get<Row>(
        `/caregiver?auth_user_id=eq.${authUserId}&role=eq.Primary%20Caregiver&select=caregiver_id,first_name,last_name,patient_id,patients(first_name,last_name)`,
      );
      if (!data[0]) return null;
      const r = data[0];
      return {
        caregiverId: r.caregiver_id,
        caregiverName: [r.first_name, r.last_name].filter(Boolean).join(' '),
        patientId: r.patient_id,
        patientName: r.patients
          ? [r.patients.first_name, r.patients.last_name].filter(Boolean).join(' ')
          : 'Patient',
      };
    } catch { return null; }
  }

  async getPatientByAuthId(authUserId: string): Promise<{
    patientId: number; patientName: string;
  } | null> {
    try {
      const { data } = await this.db.get<Array<{
        patient_id: number; first_name: string; last_name: string;
      }>>(`/patients?auth_user_id=eq.${authUserId}&select=patient_id,first_name,last_name`);
      if (!data[0]) return null;
      return {
        patientId: data[0].patient_id,
        patientName: [data[0].first_name, data[0].last_name].filter(Boolean).join(' '),
      };
    } catch { return null; }
  }

  async signIn(email: string, password: string): Promise<{
    caregiverId: number;
    caregiverName: string;
    patientId: number;
    patientName: string;
  } | null> {
    type CaregiverRow = Array<{
      caregiver_id: number;
      first_name: string;
      last_name: string;
      patient_id: number;
      patients: { first_name: string; last_name: string } | null;
    }>;

    const toResult = (row: CaregiverRow[0]) => ({
      caregiverId: row.caregiver_id,
      caregiverName: [row.first_name, row.last_name].filter(Boolean).join(' '),
      patientId: row.patient_id,
      patientName: row.patients
        ? [row.patients.first_name, row.patients.last_name].filter(Boolean).join(' ')
        : 'Patient',
    });

    console.log('[API] signIn: attempting auth for', email.toLowerCase());
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: email.toLowerCase(),
      password,
    });

    if (authError || !authData.user) {
      console.warn('[API] signIn: auth failed —', authError?.message ?? 'no user returned');
      return null;
    }
    console.log('[API] signIn: auth succeeded, user_id =', authData.user.id);

    try {
      const { data } = await this.db.get<CaregiverRow>(
        `/caregiver?auth_user_id=eq.${authData.user.id}&role=eq.Primary%20Caregiver&select=caregiver_id,first_name,last_name,patient_id,patients(first_name,last_name)`,
      );
      if (data[0]) {
        console.log('[API] signIn: caregiver found — caregiver_id =', data[0].caregiver_id, '| patient_id =', data[0].patient_id);
        return toResult(data[0]);
      }
      console.warn('[API] signIn: no caregiver row found for this auth user');
    } catch (err) {
      console.error('[API] signIn: DB query error —', err);
    }

    return null;
  }

  async signInPatient(username: string, pin: string): Promise<{
    patientId: number;
    patientName: string;
  } | null> {
    const email = `pt_${username.toLowerCase()}@example.com`;
    console.log('[API] signInPatient: attempting auth for', email);
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email,
      password: pinToPassword(pin),
    });

    if (authError || !authData.user) {
      console.warn('[API] signInPatient: auth failed —', authError?.message ?? 'no user returned');
      return null;
    }
    console.log('[API] signInPatient: auth succeeded, user_id =', authData.user.id);

    try {
      const { data } = await this.db.get<Array<{
        patient_id: number;
        first_name: string;
        last_name: string;
      }>>(
        `/patients?auth_user_id=eq.${authData.user.id}&select=patient_id,first_name,last_name`,
      );
      if (!data[0]) {
        console.warn('[API] signInPatient: no patient row found for this auth user');
        return null;
      }
      console.log('[API] signInPatient: patient found — patient_id =', data[0].patient_id);
      return {
        patientId: data[0].patient_id,
        patientName: [data[0].first_name, data[0].last_name].filter(Boolean).join(' '),
      };
    } catch (err) {
      console.error('[API] signInPatient: DB query error —', err);
      return null;
    }
  }

}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Normalize a lookup-table label: trim, collapse runs of spaces, then title-case.
 * "swim" → "Swim", "  SWIM  " → "Swim", "morning walk" → "Morning Walk"
 */
function normalizeLabel(value: string): string {
  return value
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Convert empty/undefined strings to null for nullable columns. */
function orNull(value: unknown): string | null {
  if (typeof value !== 'string' || value.trim() === '') return null;
  return value;
}

/**
 * Validate E.164 phone format required by the caregiver.contact_no CHECK constraint.
 * Returns the value if valid, null otherwise (constraint allows null).
 */
function e164OrNull(value: unknown): string | null {
  if (typeof value !== 'string' || value.trim() === '') return null;
  const v = value.trim();
  return /^\+[1-9][0-9]{7,14}$/.test(v) ? v : null;
}

/**
 * Normalise a time string to HH:MM:SS for Postgres `time` columns.
 * Accepts "HH:MM", "H:MM", or "HH:MM:SS". Returns null if unparseable.
 */
function toTime(value: string | undefined | null): string | null {
  if (!value || value.trim() === '') return null;
  const v = value.trim();
  if (/^\d{2}:\d{2}:\d{2}$/.test(v)) return v;
  if (/^\d{1,2}:\d{2}$/.test(v)) {
    const [h, m] = v.split(':');
    return `${h.padStart(2, '0')}:${m}:00`;
  }
  return null;
}

export const apiService = new ApiService();
export default apiService;
