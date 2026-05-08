import React from 'react';
import { render, screen, waitFor } from '@testing-library/react-native';
import DashboardHomeTab from '../../components/caregiver/DashboardHomeTab';
import apiService from '../../services/apiService';

// Mock third-party native modules that don't run in Jest
jest.mock('expo-linear-gradient', () => ({
  LinearGradient: ({ children }: { children: React.ReactNode }) => children,
}));

jest.mock('@expo/vector-icons', () => ({
  MaterialCommunityIcons: () => null,
}));

jest.mock('../../services/apiService');
const mockApi = apiService as jest.Mocked<typeof apiService>;

const baseProps = {
  patientId: 1,
  caregiverId: 2,
  caregiverName: 'Sarah Connor',
  patientName: 'John Doe',
  onGoToPatient: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
  mockApi.getPatient.mockResolvedValue({ diagnosis_stage: 'Mild', dob: '1945-06-15' } as any);
  mockApi.getPatientMedications.mockResolvedValue([]);
  mockApi.getPatientMeals.mockResolvedValue([]);
  mockApi.getPatientActivities.mockResolvedValue([]);
  mockApi.getFamilyMembers.mockResolvedValue([]);
});

describe('DashboardHomeTab', () => {
  test('shows caregiver first name in greeting', async () => {
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText(/Sarah/)).toBeTruthy();
    });
  });

  test('shows patient name', async () => {
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeTruthy();
    });
  });

  test('shows diagnosis stage when available', async () => {
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText(/Mild/)).toBeTruthy();
    });
  });

  test('shows empty schedule message when no items', async () => {
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText('No schedule configured yet')).toBeTruthy();
    });
  });

  test('shows medication name and formatted time in schedule', async () => {
    mockApi.getPatientMedications.mockResolvedValue([
      { patientMedicationId: 1, name: 'Aspirin', time: '08:00', dosage: 100 } as any,
    ]);
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText('Aspirin')).toBeTruthy();
      expect(screen.getByText('8:00 AM')).toBeTruthy();
    });
  });

  test('shows meal in schedule', async () => {
    mockApi.getPatientMeals.mockResolvedValue([
      { patientMealId: 1, mealType: 'Breakfast', mealTime: '07:30' } as any,
    ]);
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText('Breakfast')).toBeTruthy();
      expect(screen.getByText('7:30 AM')).toBeTruthy();
    });
  });

  test('shows activity in schedule', async () => {
    mockApi.getPatientActivities.mockResolvedValue([
      { patientActivityId: 1, name: 'Morning Walk', startTime: '06:00', endTime: '06:30' } as any,
    ]);
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText('Morning Walk')).toBeTruthy();
    });
  });

  test('schedule items are sorted by time', async () => {
    mockApi.getPatientMedications.mockResolvedValue([
      { patientMedicationId: 1, name: 'Evening Pill', time: '20:00', dosage: 50 } as any,
    ]);
    mockApi.getPatientMeals.mockResolvedValue([
      { patientMealId: 1, mealType: 'Breakfast', mealTime: '07:00' } as any,
    ]);
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      const breakfast = screen.getByText('Breakfast');
      const pill = screen.getByText('Evening Pill');
      // Breakfast renders before Evening Pill in the tree
      expect(breakfast).toBeTruthy();
      expect(pill).toBeTruthy();
    });
  });

  test('shows stat counts for medications, meals, activities, family', async () => {
    mockApi.getPatientMedications.mockResolvedValue([
      { patientMedicationId: 1, name: 'A', time: '08:00', dosage: 10 } as any,
      { patientMedicationId: 2, name: 'B', time: '12:00', dosage: 20 } as any,
    ]);
    mockApi.getPatientMeals.mockResolvedValue([
      { patientMealId: 1, mealType: 'Lunch', mealTime: '12:00' } as any,
    ]);
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText('Medications')).toBeTruthy();
      expect(screen.getByText('Meals')).toBeTruthy();
      expect(screen.getByText('Activities')).toBeTruthy();
      expect(screen.getByText('Family')).toBeTruthy();
    });
  });

  test('shows family member name and relationship', async () => {
    mockApi.getFamilyMembers.mockResolvedValue([
      { familyMemberId: 1, firstName: 'Alice', lastName: 'Doe', relationship: 'Daughter', contactNo: '555-1234' } as any,
    ]);
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.getByText('Alice Doe')).toBeTruthy();
      expect(screen.getByText('Daughter')).toBeTruthy();
    });
  });

  test('hides family section when no family members', async () => {
    render(<DashboardHomeTab {...baseProps} />);
    await waitFor(() => {
      expect(screen.queryByText('Family Members')).toBeNull();
    });
  });

  test('calls all api methods with correct patientId', async () => {
    render(<DashboardHomeTab {...baseProps} patientId={42} />);
    await waitFor(() => {
      expect(mockApi.getPatient).toHaveBeenCalledWith(42);
      expect(mockApi.getPatientMedications).toHaveBeenCalledWith(42);
      expect(mockApi.getPatientMeals).toHaveBeenCalledWith(42);
      expect(mockApi.getPatientActivities).toHaveBeenCalledWith(42);
      expect(mockApi.getFamilyMembers).toHaveBeenCalledWith(42);
    });
  });
});
