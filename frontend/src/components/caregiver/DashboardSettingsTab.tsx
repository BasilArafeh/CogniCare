import React, { useCallback, useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  StyleSheet, ActivityIndicator, Alert, RefreshControl,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import apiService, {
  type MedDisplay, type MealDisplay, type ActivityDisplay,
  type FamilyDisplay, type EmergencyContactDisplay, type PatientRow,
} from '../../services/apiService';
import TimePickerModal from '../TimePickerModal';

interface Props {
  patientId: number;
  caregiverId: number;
}

const MEAL_TYPES = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];
const DIAGNOSIS_STAGES = ['Mild', 'Moderate', 'Severe'];

function formatTime(t: string): string {
  if (!t) return '—';
  const [hStr, mStr] = t.split(':');
  const h = parseInt(hStr, 10);
  const period = h >= 12 ? 'PM' : 'AM';
  return `${h % 12 || 12}:${(mStr ?? '00').padStart(2, '0')} ${period}`;
}

function confirmDelete(title: string, msg: string, onConfirm: () => void) {
  Alert.alert(title, msg, [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Remove', style: 'destructive', onPress: onConfirm },
  ]);
}

// ─── Shared small helpers ──────────────────────────────────────────────────────

function Field({
  label, value, onChangeText, placeholder, icon, keyboardType, multiline,
}: {
  label: string; value: string; onChangeText: (v: string) => void;
  placeholder: string; icon: string; keyboardType?: any; multiline?: boolean;
}) {
  return (
    <View style={fS.fieldWrap}>
      <Text style={fS.fieldLabel}>{label}</Text>
      <View style={[fS.inputRow, multiline && { alignItems: 'flex-start', paddingTop: 10 }]}>
        <MaterialCommunityIcons name={icon as any} size={15} color={colors.textMuted} style={{ marginRight: 8, marginTop: multiline ? 2 : 0 }} />
        <TextInput
          style={[fS.input, multiline && { minHeight: 60 }]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textMuted}
          keyboardType={keyboardType}
          multiline={multiline}
        />
      </View>
    </View>
  );
}

function TimeField({ label, time, onPress }: { label: string; time: string; onPress: () => void }) {
  return (
    <View style={fS.fieldWrap}>
      <Text style={fS.fieldLabel}>{label}</Text>
      <TouchableOpacity onPress={onPress} style={fS.timeBtn}>
        <MaterialCommunityIcons name="clock-outline" size={15} color={time ? colors.primary : colors.textMuted} />
        <Text style={[fS.timeBtnText, !time && { color: colors.textMuted }]}>
          {time ? formatTime(time) : 'Select time'}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

function PillSelect({ label, options, value, onChange }: {
  label: string; options: string[]; value: string; onChange: (v: string) => void;
}) {
  return (
    <View style={fS.fieldWrap}>
      <Text style={fS.fieldLabel}>{label}</Text>
      <View style={fS.pillRow}>
        {options.map((opt) => (
          <TouchableOpacity
            key={opt}
            onPress={() => onChange(opt)}
            style={[fS.pill, value === opt && fS.pillActive]}
          >
            <Text style={[fS.pillText, value === opt && fS.pillTextActive]}>{opt}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

function FormActions({ onSave, onCancel, saving, isEditing = false }: {
  onSave: () => void; onCancel: () => void; saving: boolean; isEditing?: boolean;
}) {
  return (
    <View style={fS.actions}>
      <TouchableOpacity onPress={onCancel} style={fS.cancelBtn}>
        <Text style={fS.cancelText}>Cancel</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={onSave} style={fS.saveBtn} disabled={saving}>
        {saving ? <ActivityIndicator color={colors.white} size="small" /> : (
          <>
            <MaterialCommunityIcons name="check" size={15} color={colors.white} />
            <Text style={fS.saveText}>{isEditing ? 'Update' : 'Save'}</Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );
}

// ─── Patient Info ──────────────────────────────────────────────────────────────

function PatientInfoSection({ patient, patientId, onUpdated }: {
  patient: PatientRow; patientId: number; onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [firstName, setFirstName] = useState(patient.first_name ?? '');
  const [lastName, setLastName] = useState(patient.last_name ?? '');
  const [gender, setGender] = useState(patient.gender ?? '');
  const [dob, setDob] = useState(patient.dob ?? '');
  const [address, setAddress] = useState(patient.address ?? '');
  const [phone, setPhone] = useState(patient.contact_no ?? '');
  const [stage, setStage] = useState(patient.diagnosis_stage ?? '');
  const [saving, setSaving] = useState(false);

  const startEdit = () => {
    setFirstName(patient.first_name ?? '');
    setLastName(patient.last_name ?? '');
    setGender(patient.gender ?? '');
    setDob(patient.dob ?? '');
    setAddress(patient.address ?? '');
    setPhone(patient.contact_no ?? '');
    setStage(patient.diagnosis_stage ?? '');
    setEditing(true);
  };

  const handleSave = async () => {
    if (!firstName.trim()) { Alert.alert('Required', "Enter patient's first name"); return; }
    setSaving(true);
    try {
      await apiService.editPatient(patientId, {
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        gender,
        dob: dob.trim(),
        address: address.trim(),
        contactNo: phone.trim(),
        diagnosisStage: stage,
      });
      setEditing(false);
      onUpdated();
    } catch {
      Alert.alert('Error', 'Failed to update patient info.');
    } finally {
      setSaving(false);
    }
  };

  const infoRows = [
    { icon: 'account', label: 'Name', val: [patient.first_name, patient.last_name].filter(Boolean).join(' ') || '—' },
    { icon: 'gender-male-female', label: 'Gender', val: patient.gender || '—' },
    { icon: 'calendar-heart', label: 'Date of Birth', val: patient.dob || '—' },
    { icon: 'stethoscope', label: 'Diagnosis Stage', val: patient.diagnosis_stage || '—' },
    { icon: 'map-marker', label: 'Address', val: patient.address || '—' },
    { icon: 'phone', label: 'Phone', val: patient.contact_no || '—' },
  ];

  return (
    <View style={sS.section}>
      <View style={sS.sectionHeader}>
        <View style={[sS.iconWrap, { backgroundColor: withAlpha('#7C5CBF', 0.12) }]}>
          <MaterialCommunityIcons name="account-heart" size={16} color="#7C5CBF" />
        </View>
        <Text style={sS.sectionTitle}>Patient Info</Text>
        {!editing && (
          <TouchableOpacity onPress={startEdit} style={sS.editHeaderBtn}>
            <MaterialCommunityIcons name="pencil-outline" size={16} color={colors.primary} />
            <Text style={sS.editHeaderText}>Edit</Text>
          </TouchableOpacity>
        )}
      </View>

      {editing ? (
        <View style={fS.wrap}>
          <View style={fS.row}>
            <View style={{ flex: 1, marginRight: 8 }}>
              <Field label="First Name *" value={firstName} onChangeText={setFirstName} placeholder="First" icon="account" />
            </View>
            <View style={{ flex: 1 }}>
              <Field label="Last Name" value={lastName} onChangeText={setLastName} placeholder="Last" icon="account" />
            </View>
          </View>
          <PillSelect label="Gender" options={['Male', 'Female', 'Other']} value={gender} onChange={setGender} />
          <Field label="Date of Birth" value={dob} onChangeText={setDob} placeholder="YYYY-MM-DD" icon="calendar" />
          <PillSelect label="Diagnosis Stage" options={DIAGNOSIS_STAGES} value={stage} onChange={setStage} />
          <Field label="Address" value={address} onChangeText={setAddress} placeholder="Street, City" icon="map-marker" />
          <Field label="Phone" value={phone} onChangeText={setPhone} placeholder="+1234567890" icon="phone" keyboardType="phone-pad" />
          <FormActions onSave={handleSave} onCancel={() => setEditing(false)} saving={saving} isEditing />
        </View>
      ) : (
        <View style={sS.infoGrid}>
          {infoRows.map((row) => (
            <View key={row.label} style={sS.infoRow}>
              <MaterialCommunityIcons name={row.icon as any} size={14} color={colors.textMuted} />
              <Text style={sS.infoLabel}>{row.label}</Text>
              <Text style={sS.infoVal} numberOfLines={1}>{row.val}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

// ─── Medication Form ───────────────────────────────────────────────────────────

function MedForm({ initial, onSave, onCancel }: {
  initial?: MedDisplay;
  onSave: (name: string, dosage: string, time: string, notes: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [dosage, setDosage] = useState(initial?.dosage ?? '');
  const [time, setTime] = useState(initial?.time ?? '');
  const [notes, setNotes] = useState(initial?.notes ?? '');
  const [showPicker, setShowPicker] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) { Alert.alert('Required', 'Enter medication name'); return; }
    setSaving(true);
    try { await onSave(name.trim(), dosage.trim(), time, notes.trim()); }
    finally { setSaving(false); }
  };

  return (
    <View style={fS.wrap}>
      <TimePickerModal visible={showPicker} initialTime={time} title="Medication Time"
        onConfirm={(t) => { setTime(t); setShowPicker(false); }} onCancel={() => setShowPicker(false)} />
      <Field label="Medication Name *" value={name} onChangeText={setName} placeholder="e.g. Donepezil" icon="pill" />
      <View style={fS.row}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <Field label="Dosage (mg)" value={dosage} onChangeText={setDosage} placeholder="e.g. 10" keyboardType="decimal-pad" icon="weight" />
        </View>
        <View style={{ flex: 1 }}>
          <TimeField label="Time" time={time} onPress={() => setShowPicker(true)} />
        </View>
      </View>
      <Field label="Notes" value={notes} onChangeText={setNotes} placeholder="Special instructions…" icon="note-text" />
      <FormActions onSave={handleSave} onCancel={onCancel} saving={saving} isEditing={!!initial} />
    </View>
  );
}

// ─── Meal Form ─────────────────────────────────────────────────────────────────

function MealForm({ initial, onSave, onCancel }: {
  initial?: MealDisplay;
  onSave: (mealName: string, mealTime: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [mealName, setMealName] = useState(initial?.mealType ?? '');
  const [mealTime, setMealTime] = useState(initial?.mealTime ?? '');
  const [showPicker, setShowPicker] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!mealName.trim()) { Alert.alert('Required', 'Select a meal type'); return; }
    setSaving(true);
    try { await onSave(mealName, mealTime); }
    finally { setSaving(false); }
  };

  return (
    <View style={fS.wrap}>
      <TimePickerModal visible={showPicker} initialTime={mealTime} title="Meal Time"
        onConfirm={(t) => { setMealTime(t); setShowPicker(false); }} onCancel={() => setShowPicker(false)} />
      <PillSelect label="Meal Type *" options={MEAL_TYPES} value={mealName} onChange={setMealName} />
      <TimeField label="Meal Time" time={mealTime} onPress={() => setShowPicker(true)} />
      <FormActions onSave={handleSave} onCancel={onCancel} saving={saving} isEditing={!!initial} />
    </View>
  );
}

// ─── Activity Form ─────────────────────────────────────────────────────────────

function ActivityForm({ initial, onSave, onCancel }: {
  initial?: ActivityDisplay;
  onSave: (name: string, start: string, end: string, desc: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [start, setStart] = useState(initial?.startTime ?? '');
  const [end, setEnd] = useState(initial?.endTime ?? '');
  const [desc, setDesc] = useState(initial?.description ?? '');
  const [pickerField, setPickerField] = useState<'start' | 'end' | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) { Alert.alert('Required', 'Enter activity name'); return; }
    setSaving(true);
    try { await onSave(name.trim(), start, end, desc.trim()); }
    finally { setSaving(false); }
  };

  return (
    <View style={fS.wrap}>
      <TimePickerModal
        visible={pickerField !== null}
        initialTime={pickerField === 'start' ? start : end}
        title={pickerField === 'start' ? 'Start Time' : 'End Time'}
        onConfirm={(t) => { pickerField === 'start' ? setStart(t) : setEnd(t); setPickerField(null); }}
        onCancel={() => setPickerField(null)}
      />
      <Field label="Activity Name *" value={name} onChangeText={setName} placeholder="e.g. Morning Walk" icon="shoe-sneaker" />
      <View style={fS.row}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <TimeField label="Start Time" time={start} onPress={() => setPickerField('start')} />
        </View>
        <View style={{ flex: 1 }}>
          <TimeField label="End Time" time={end} onPress={() => setPickerField('end')} />
        </View>
      </View>
      <Field label="Description" value={desc} onChangeText={setDesc} placeholder="Brief description…" icon="text" multiline />
      <FormActions onSave={handleSave} onCancel={onCancel} saving={saving} isEditing={!!initial} />
    </View>
  );
}

// ─── Family Member Form ────────────────────────────────────────────────────────

function FamilyForm({ initial, onSave, onCancel }: {
  initial?: FamilyDisplay;
  onSave: (firstName: string, lastName: string, relationship: string, contactNo: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [firstName, setFirstName] = useState(initial?.firstName ?? '');
  const [lastName, setLastName] = useState(initial?.lastName ?? '');
  const [rel, setRel] = useState(initial?.relationship ?? '');
  const [phone, setPhone] = useState(initial?.contactNo ?? '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!firstName.trim()) { Alert.alert('Required', 'Enter first name'); return; }
    setSaving(true);
    try { await onSave(firstName.trim(), lastName.trim(), rel.trim(), phone.trim()); }
    finally { setSaving(false); }
  };

  return (
    <View style={fS.wrap}>
      <View style={fS.row}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <Field label="First Name *" value={firstName} onChangeText={setFirstName} placeholder="First" icon="account" />
        </View>
        <View style={{ flex: 1 }}>
          <Field label="Last Name" value={lastName} onChangeText={setLastName} placeholder="Last" icon="account" />
        </View>
      </View>
      <Field label="Relationship" value={rel} onChangeText={setRel} placeholder="e.g. Son, Daughter" icon="account-heart" />
      <Field label="Phone" value={phone} onChangeText={setPhone} placeholder="+1234567890" icon="phone" keyboardType="phone-pad" />
      <FormActions onSave={handleSave} onCancel={onCancel} saving={saving} isEditing={!!initial} />
    </View>
  );
}

// ─── Emergency Contact Form ────────────────────────────────────────────────────

function ContactForm({ initial, onSave, onCancel }: {
  initial?: EmergencyContactDisplay;
  onSave: (name: string, phone: string, relationship: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [phone, setPhone] = useState(initial?.phone ?? '');
  const [rel, setRel] = useState(initial?.relationship ?? '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) { Alert.alert('Required', 'Enter contact name'); return; }
    if (!phone.trim()) { Alert.alert('Required', 'Enter phone number'); return; }
    setSaving(true);
    try { await onSave(name.trim(), phone.trim(), rel.trim()); }
    finally { setSaving(false); }
  };

  return (
    <View style={fS.wrap}>
      <Field label="Full Name *" value={name} onChangeText={setName} placeholder="e.g. Dr. Sarah" icon="account-alert" />
      <Field label="Phone *" value={phone} onChangeText={setPhone} placeholder="+1234567890" icon="phone-alert" keyboardType="phone-pad" />
      <Field label="Relationship / Role" value={rel} onChangeText={setRel} placeholder="e.g. Doctor, Neighbor" icon="account-tie" />
      <FormActions onSave={handleSave} onCancel={onCancel} saving={saving} isEditing={!!initial} />
    </View>
  );
}

// ─── ItemRow ───────────────────────────────────────────────────────────────────

function ItemRow({ icon, iconColor, title, sub, onEdit, onDelete }: {
  icon: string; iconColor: string; title: string; sub: string;
  onEdit: () => void; onDelete: () => void;
}) {
  return (
    <View style={sS.itemRow}>
      <View style={[sS.itemIconWrap, { backgroundColor: withAlpha(iconColor, 0.1) }]}>
        <MaterialCommunityIcons name={icon as any} size={14} color={iconColor} />
      </View>
      <View style={sS.itemInfo}>
        <Text style={sS.itemTitle}>{title}</Text>
        {!!sub && <Text style={sS.itemSub}>{sub}</Text>}
      </View>
      <TouchableOpacity onPress={onEdit} style={sS.actionBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
        <MaterialCommunityIcons name="pencil-outline" size={17} color={colors.primary} />
      </TouchableOpacity>
      <TouchableOpacity onPress={onDelete} style={sS.actionBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
        <MaterialCommunityIcons name="delete-outline" size={17} color={colors.error} />
      </TouchableOpacity>
    </View>
  );
}

function AddButton({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <TouchableOpacity onPress={onPress} style={sS.addBtn} activeOpacity={0.7}>
      <MaterialCommunityIcons name="plus-circle-outline" size={17} color={colors.primary} />
      <Text style={sS.addBtnText}>{label}</Text>
    </TouchableOpacity>
  );
}

function Section({ icon, iconColor, title, children }: {
  icon: string; iconColor: string; title: string; children: React.ReactNode;
}) {
  return (
    <View style={sS.section}>
      <View style={sS.sectionHeader}>
        <View style={[sS.iconWrap, { backgroundColor: withAlpha(iconColor, 0.12) }]}>
          <MaterialCommunityIcons name={icon as any} size={16} color={iconColor} />
        </View>
        <Text style={sS.sectionTitle}>{title}</Text>
      </View>
      {children}
    </View>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────

export default function DashboardSettingsTab({ patientId }: Props) {
  const [patient, setPatient] = useState<PatientRow | null>(null);
  const [meds, setMeds] = useState<MedDisplay[]>([]);
  const [meals, setMeals] = useState<MealDisplay[]>([]);
  const [activities, setActivities] = useState<ActivityDisplay[]>([]);
  const [family, setFamily] = useState<FamilyDisplay[]>([]);
  const [contacts, setContacts] = useState<EmergencyContactDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [adding, setAdding] = useState<'med' | 'meal' | 'activity' | 'family' | 'contact' | null>(null);
  const [editingMedId, setEditingMedId] = useState<number | null>(null);
  const [editingMealId, setEditingMealId] = useState<number | null>(null);
  const [editingActivityId, setEditingActivityId] = useState<number | null>(null);
  const [editingFamilyId, setEditingFamilyId] = useState<number | null>(null);
  const [editingContactId, setEditingContactId] = useState<number | null>(null);

  const fetchAll = useCallback(async () => {
    const [pt, m, ml, ac, fm, ec] = await Promise.all([
      apiService.getPatient(patientId),
      apiService.getPatientMedications(patientId),
      apiService.getPatientMeals(patientId),
      apiService.getPatientActivities(patientId),
      apiService.getFamilyMembers(patientId),
      apiService.getEmergencyContacts(patientId),
    ]);
    setPatient(pt);
    setMeds(m);
    setMeals(ml);
    setActivities(ac);
    setFamily(fm);
    setContacts(ec);
  }, [patientId]);

  useEffect(() => {
    setLoading(true);
    fetchAll().finally(() => setLoading(false));
  }, [fetchAll]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchAll().finally(() => setRefreshing(false));
  }, [fetchAll]);

  const closeAll = () => {
    setAdding(null);
    setEditingMedId(null);
    setEditingMealId(null);
    setEditingActivityId(null);
    setEditingFamilyId(null);
    setEditingContactId(null);
  };

  const startAdding = (type: typeof adding) => { closeAll(); setAdding(type); };
  const startEditMed = (id: number) => { closeAll(); setEditingMedId(id); };
  const startEditMeal = (id: number) => { closeAll(); setEditingMealId(id); };
  const startEditActivity = (id: number) => { closeAll(); setEditingActivityId(id); };
  const startEditFamily = (id: number) => { closeAll(); setEditingFamilyId(id); };
  const startEditContact = (id: number) => { closeAll(); setEditingContactId(id); };

  if (loading) {
    return (
      <View style={sS.loadingWrap}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <ScrollView
      style={sS.scroll}
      contentContainerStyle={sS.content}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
    >
      <Text style={sS.pageTitle}>Care Settings</Text>
      <Text style={sS.pageSub}>Manage all patient care information</Text>

      {/* ── Patient Info ── */}
      {patient && (
        <PatientInfoSection patient={patient} patientId={patientId} onUpdated={fetchAll} />
      )}

      {/* ── Medications ── */}
      <Section icon="pill" iconColor={colors.primary} title="Medications">
        {meds.map((med, index) => {
          const medKey = med.patientMedicationId ?? `missing-${med.medicationId ?? index}`;
          return editingMedId === med.patientMedicationId ? (
            <MedForm
              key={`edit-med-${medKey}`}
              initial={med}
              onSave={async (n, d, t, nt) => {
                await apiService.editMedication(med.patientMedicationId, med.medicationId, n, d, t, nt);
                setEditingMedId(null);
                await fetchAll();
              }}
              onCancel={() => setEditingMedId(null)}
            />
          ) : (
            <ItemRow
              key={`med-${medKey}`}
              icon="pill"
              iconColor={colors.primary}
              title={med.name}
              sub={[med.dosage ? `${med.dosage}mg` : null, formatTime(med.time), med.notes].filter(Boolean).join(' · ')}
              onEdit={() => startEditMed(med.patientMedicationId)}
              onDelete={() => confirmDelete('Remove Medication', `Remove "${med.name}"?`, async () => {
                try {
                  await apiService.deleteMedication(med.patientMedicationId, med.medicationId);
                  await fetchAll();
                } catch { Alert.alert('Error', 'Failed to remove medication.'); }
              })}
            />
          );
        })}
        {adding === 'med' ? (
          <MedForm
            onSave={async (n, d, t, nt) => {
              await apiService.addMedication(patientId, n, d, t, nt);
              setAdding(null);
              await fetchAll();
            }}
            onCancel={() => setAdding(null)}
          />
        ) : (
          <AddButton label="Add Medication" onPress={() => startAdding('med')} />
        )}
      </Section>

      {/* ── Meals ── */}
      <Section icon="silverware-fork-knife" iconColor={colors.secondary} title="Meals">
        {meals.map((meal, index) => {
          const mealKey = meal.patientMealId ?? `missing-${meal.mealId ?? index}`;
          return editingMealId === meal.patientMealId ? (
            <MealForm
              key={`edit-meal-${mealKey}`}
              initial={meal}
              onSave={async (mn, mt) => {
                await apiService.editMeal(meal.patientMealId, meal.mealId, mn, mt);
                setEditingMealId(null);
                await fetchAll();
              }}
              onCancel={() => setEditingMealId(null)}
            />
          ) : (
            <ItemRow
              key={`meal-${mealKey}`}
              icon="silverware-fork-knife"
              iconColor={colors.secondary}
              title={meal.mealType}
              sub={formatTime(meal.mealTime)}
              onEdit={() => startEditMeal(meal.patientMealId)}
              onDelete={() => confirmDelete('Remove Meal', `Remove "${meal.mealType}"?`, async () => {
                try {
                  await apiService.deleteMeal(meal.patientMealId, meal.mealId);
                  await fetchAll();
                } catch { Alert.alert('Error', 'Failed to remove meal.'); }
              })}
            />
          );
        })}
        {adding === 'meal' ? (
          <MealForm
            onSave={async (mn, mt) => {
              await apiService.addMeal(patientId, mn, mt);
              setAdding(null);
              await fetchAll();
            }}
            onCancel={() => setAdding(null)}
          />
        ) : (
          <AddButton label="Add Meal" onPress={() => startAdding('meal')} />
        )}
      </Section>

      {/* ── Activities ── */}
      <Section icon="run-fast" iconColor="#F59E0B" title="Daily Activities">
        {activities.map((act, index) => {
          const actKey = act.patientActivityId ?? `missing-${act.activityId ?? index}`;
          return editingActivityId === act.patientActivityId ? (
            <ActivityForm
              key={`edit-act-${actKey}`}
              initial={act}
              onSave={async (n, s, e, d) => {
                await apiService.editActivity(act.patientActivityId, act.activityId, n, s, e, d);
                setEditingActivityId(null);
                await fetchAll();
              }}
              onCancel={() => setEditingActivityId(null)}
            />
          ) : (
            <ItemRow
              key={`act-${actKey}`}
              icon="run-fast"
              iconColor="#F59E0B"
              title={act.name}
              sub={[formatTime(act.startTime), act.endTime ? `→ ${formatTime(act.endTime)}` : null, act.description].filter(Boolean).join(' · ')}
              onEdit={() => startEditActivity(act.patientActivityId)}
              onDelete={() => confirmDelete('Remove Activity', `Remove "${act.name}"?`, async () => {
                try {
                  await apiService.deleteActivity(act.patientActivityId, act.activityId);
                  await fetchAll();
                } catch { Alert.alert('Error', 'Failed to remove activity.'); }
              })}
            />
          );
        })}
        {adding === 'activity' ? (
          <ActivityForm
            onSave={async (n, s, e, d) => {
              await apiService.addActivity(patientId, n, s, e, d);
              setAdding(null);
              await fetchAll();
            }}
            onCancel={() => setAdding(null)}
          />
        ) : (
          <AddButton label="Add Activity" onPress={() => startAdding('activity')} />
        )}
      </Section>

      {/* ── Family Members ── */}
      <Section icon="account-group" iconColor={colors.primaryDark} title="Family Members">
        {family.map((f, index) => {
          const famKey = f.familyMemberId ?? `missing-fam-${index}`;
          return editingFamilyId === f.familyMemberId ? (
            <FamilyForm
              key={`edit-fam-${famKey}`}
              initial={f}
              onSave={async (fn, ln, r, c) => {
                await apiService.editFamilyMember(f.familyMemberId, fn, ln, r, c);
                setEditingFamilyId(null);
                await fetchAll();
              }}
              onCancel={() => setEditingFamilyId(null)}
            />
          ) : (
            <ItemRow
              key={`fam-${famKey}`}
              icon="account-group"
              iconColor={colors.primaryDark}
              title={[f.firstName, f.lastName].filter(Boolean).join(' ')}
              sub={[f.relationship, f.contactNo].filter(Boolean).join(' · ')}
              onEdit={() => startEditFamily(f.familyMemberId)}
              onDelete={() => confirmDelete('Remove Family Member', `Remove "${f.firstName}"?`, async () => {
                try {
                  await apiService.deleteFamilyMember(f.familyMemberId);
                  await fetchAll();
                } catch { Alert.alert('Error', 'Failed to remove family member.'); }
              })}
            />
          );
        })}
        {adding === 'family' ? (
          <FamilyForm
            onSave={async (fn, ln, r, c) => {
              await apiService.addFamilyMember(patientId, fn, ln, r, c);
              setAdding(null);
              await fetchAll();
            }}
            onCancel={() => setAdding(null)}
          />
        ) : (
          <AddButton label="Add Family Member" onPress={() => startAdding('family')} />
        )}
      </Section>

      {/* ── Emergency Contacts ── */}
      <Section icon="phone-alert" iconColor={colors.error} title="Emergency Contacts">
        {contacts.map((c, index) => {
          const ecKey = c.caregiverPriorityId ?? `missing-ec-${index}`;
          return editingContactId === c.caregiverPriorityId ? (
            <ContactForm
              key={`edit-ec-${ecKey}`}
              initial={c}
              onSave={async (n, p, r) => {
                await apiService.editEmergencyContact(c.caregiverId, n, p, r);
                setEditingContactId(null);
                await fetchAll();
              }}
              onCancel={() => setEditingContactId(null)}
            />
          ) : (
            <ItemRow
              key={`ec-${ecKey}`}
              icon="phone-alert"
              iconColor={colors.error}
              title={c.name}
              sub={[c.relationship, c.phone].filter(Boolean).join(' · ')}
              onEdit={() => startEditContact(c.caregiverPriorityId)}
              onDelete={() => confirmDelete('Remove Contact', `Remove "${c.name}"?`, async () => {
                try {
                  await apiService.deleteEmergencyContact(c.caregiverId, c.caregiverPriorityId);
                  await fetchAll();
                } catch { Alert.alert('Error', 'Failed to remove contact.'); }
              })}
            />
          );
        })}
        {adding === 'contact' ? (
          <ContactForm
            onSave={async (n, p, r) => {
              await apiService.addEmergencyContact(patientId, n, p, r);
              setAdding(null);
              await fetchAll();
            }}
            onCancel={() => setAdding(null)}
          />
        ) : (
          <AddButton label="Add Emergency Contact" onPress={() => startAdding('contact')} />
        )}
      </Section>
    </ScrollView>
  );
}

// ─── Section styles ────────────────────────────────────────────────────────────

const sS = StyleSheet.create({
  scroll: { flex: 1 },
  content: { padding: 20, paddingBottom: 32 },
  loadingWrap: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  pageTitle: {
    fontSize: 22,
    fontFamily: fonts.extraBold,
    color: colors.textPrimary,
    marginBottom: 3,
  },
  pageSub: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginBottom: 22,
  },
  section: {
    marginBottom: 20,
    backgroundColor: colors.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.1),
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
    overflow: 'hidden',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 13,
    borderBottomWidth: 1,
    borderBottomColor: withAlpha(colors.textMuted, 0.1),
  },
  iconWrap: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sectionTitle: {
    flex: 1,
    fontSize: 14,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  editHeaderBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    backgroundColor: withAlpha(colors.primary, 0.08),
  },
  editHeaderText: {
    fontSize: 12,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
  infoGrid: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 10,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  infoLabel: {
    fontSize: 12,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    width: 110,
  },
  infoVal: {
    flex: 1,
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 11,
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: withAlpha(colors.textMuted, 0.08),
  },
  itemIconWrap: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemInfo: { flex: 1 },
  itemTitle: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textPrimary,
  },
  itemSub: {
    fontSize: 11,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginTop: 1,
  },
  actionBtn: { padding: 4 },
  addBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 13,
  },
  addBtnText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
});

// ─── Form styles ───────────────────────────────────────────────────────────────

const fS = StyleSheet.create({
  wrap: {
    padding: 14,
    backgroundColor: withAlpha(colors.primaryLight, 0.6),
    borderTopWidth: 1,
    borderTopColor: withAlpha(colors.primary, 0.1),
    gap: 2,
  },
  row: { flexDirection: 'row' },
  fieldWrap: { marginBottom: 10 },
  fieldLabel: {
    fontSize: 11,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 5,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.textMuted, 0.28),
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  input: {
    flex: 1,
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
  },
  timeBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    backgroundColor: colors.white,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.textMuted, 0.28),
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  timeBtnText: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 7,
  },
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: withAlpha(colors.textMuted, 0.3),
    backgroundColor: colors.white,
  },
  pillActive: {
    borderColor: colors.primary,
    backgroundColor: withAlpha(colors.primary, 0.1),
  },
  pillText: {
    fontSize: 12,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  pillTextActive: {
    color: colors.primary,
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 6,
  },
  cancelBtn: {
    flex: 1,
    height: 40,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.textMuted, 0.3),
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  saveBtn: {
    flex: 2,
    height: 40,
    borderRadius: 10,
    backgroundColor: colors.primary,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  saveText: {
    fontSize: 13,
    fontFamily: fonts.bold,
    color: colors.white,
  },
});
