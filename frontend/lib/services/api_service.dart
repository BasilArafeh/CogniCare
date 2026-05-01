import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Base URL for the external REST API backend.
/// Override via --dart-define=API_BASE_URL=http://your-server:8000
const String _baseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  late final Dio _dio;

  ApiService._internal() {
    _dio = Dio(
      BaseOptions(
        baseUrl: _baseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 60),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    if (kDebugMode) {
      _dio.interceptors.add(
        LogInterceptor(
          requestBody: true,
          responseBody: false,
          logPrint: (o) => debugPrint('[API] $o'),
        ),
      );
    }
  }

  /// Exposes the underlying Dio instance for advanced use (e.g. blob URL reads).
  Dio get dio => _dio;

  // ---------------------------------------------------------------------------
  // Setup — POST /setup
  // ---------------------------------------------------------------------------

  /// Sends the full onboarding payload to the backend.
  /// Returns the response data map on success, throws [ApiException] on failure.
  Future<Map<String, dynamic>> postSetup(Map<String, dynamic> payload) async {
    try {
      final response = await _dio.post('/setup', data: payload);
      return (response.data as Map<String, dynamic>?) ?? {};
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  // ---------------------------------------------------------------------------
  // Voice — POST /patients/:id/voice
  // ---------------------------------------------------------------------------

  /// Sends a recorded audio blob to the backend and returns the response audio
  /// as raw bytes (WAV/webm).
  Future<Uint8List> postVoice({
    required String patientId,
    required Uint8List audioBytes,
    String mimeType = 'audio/webm',
  }) async {
    try {
      final formData = FormData.fromMap({
        'audio': MultipartFile.fromBytes(
          audioBytes,
          filename: 'voice.webm',
          contentType: DioMediaType.parse(mimeType),
        ),
      });

      final response = await _dio.post(
        '/patients/$patientId/voice',
        data: formData,
        options: Options(
          responseType: ResponseType.bytes,
          headers: {'Content-Type': 'multipart/form-data'},
        ),
      );

      return Uint8List.fromList(response.data as List<int>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }
}

// ---------------------------------------------------------------------------
// Payload builder
// ---------------------------------------------------------------------------

/// Transforms the wizard's collected data maps into the shape expected by
/// POST /setup.
Map<String, dynamic> buildPayload({
  required Map<String, dynamic> caregiverData,
  required Map<String, dynamic> patientData,
  required List<Map<String, dynamic>> medications,
  required List<Map<String, dynamic>> meals,
  required List<Map<String, dynamic>> activities,
  required List<Map<String, dynamic>> familyMembers,
  required List<Map<String, dynamic>> emergencyContacts,
}) {
  // Caregiver — split full name into first/last
  final nameParts = ((caregiverData['name'] as String?) ?? '').trim().split(
    ' ',
  );
  final firstName = nameParts.isNotEmpty ? nameParts.first : '';
  final lastName = nameParts.length > 1 ? nameParts.sublist(1).join(' ') : '';

  // Meals — collapse list into the expected object shape
  // Backend expects: { breakfast, lunch, dinner, dietary_restrictions }
  final mealsMap = <String, dynamic>{};
  final dietaryParts = <String>[];
  final mealKeys = ['breakfast', 'lunch', 'dinner', 'snack'];
  for (int i = 0; i < meals.length; i++) {
    final m = meals[i];
    final key = i < mealKeys.length ? mealKeys[i] : 'meal_${i + 1}';
    mealsMap[key] = m['name'] ?? '';
    final dietary = (m['dietary'] as String?) ?? '';
    if (dietary.isNotEmpty) dietaryParts.add(dietary);
  }
  mealsMap['dietary_restrictions'] = dietaryParts.join(', ');

  // Medications — map to { name, dose, time, notes }
  final medicationsPayload = medications
      .map(
        (med) => {
          'name': med['name'] ?? '',
          'dose': med['dosage'] ?? '',
          'time': med['time'] ?? '',
          'notes': med['notes'] ?? '',
        },
      )
      .toList();

  // Routines — map activities to { time, activity }
  final routinesPayload = activities
      .map((act) => {'time': act['time'] ?? '', 'activity': act['name'] ?? ''})
      .toList();

  // Family members — { name, relation, phone, email }
  final familyPayload = familyMembers
      .map(
        (fm) => {
          'name': fm['name'] ?? '',
          'relation': fm['relationship'] ?? '',
          'phone': fm['phone'] ?? '',
          'email': fm['email'] ?? '',
        },
      )
      .toList();

  // Emergency contacts — { name, relation, phone }
  final contactsPayload = emergencyContacts
      .map(
        (c) => {
          'name': c['name'] ?? '',
          'relation': c['relationship'] ?? '',
          'phone': c['phone'] ?? '',
        },
      )
      .toList();

  return {
    'caregiver': {
      'first_name': firstName,
      'last_name': lastName,
      'email': caregiverData['email'] ?? '',
      'phone': caregiverData['phone'] ?? '',
      'password': caregiverData['password'] ?? '',
    },
    'patient': {
      'name': patientData['name'] ?? '',
      'age': int.tryParse((patientData['age'] ?? '').toString()) ?? 0,
      'username': patientData['username'] ?? '',
      'password': patientData['pin'] ?? '',
    },
    'medications': medicationsPayload,
    'meals': mealsMap,
    'routines': routinesPayload,
    'family_members': familyPayload,
    'contacts': contactsPayload,
  };
}

// ---------------------------------------------------------------------------
// Error model
// ---------------------------------------------------------------------------

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  factory ApiException.fromDio(DioException e) {
    final code = e.response?.statusCode;
    final body = e.response?.data;
    String msg;
    if (body is Map && body['detail'] != null) {
      msg = body['detail'].toString();
    } else if (body is Map && body['message'] != null) {
      msg = body['message'].toString();
    } else if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      msg = 'Connection timed out. Please check your network.';
    } else if (e.type == DioExceptionType.connectionError) {
      msg = 'Cannot reach the server. Please check the API URL.';
    } else {
      msg = e.message ?? 'An unexpected error occurred.';
    }
    return ApiException(msg, statusCode: code);
  }

  @override
  String toString() => 'ApiException($statusCode): $message';
}
