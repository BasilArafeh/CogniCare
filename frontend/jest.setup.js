// Provide fake Supabase credentials so supabaseClient.ts initializes without throwing
process.env.EXPO_PUBLIC_SUPABASE_URL = 'https://fake.supabase.co';
process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY = 'fakeapikey';
