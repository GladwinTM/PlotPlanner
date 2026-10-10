import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { getEnv } from './env'

let client: SupabaseClient | undefined

/** Browser Supabase client. Uses the publishable key only; sessions persist in localStorage. */
export function getSupabase(): SupabaseClient {
  if (!client) {
    const env = getEnv()
    client = createClient(env.supabaseUrl, env.supabasePublishableKey)
  }
  return client
}
