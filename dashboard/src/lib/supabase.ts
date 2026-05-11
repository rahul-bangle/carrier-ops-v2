import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://pzasaxdmufmhrxdppsbk.supabase.co";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB6YXNheGRtdWZtaHJ4ZHBwc2JrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUzOTc0OTcsImV4cCI6MjA5MDk3MzQ5N30.JPdgodqW17oULZ4RGvr5KyUE_DqS98JEb07hOD9ss9A";

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
