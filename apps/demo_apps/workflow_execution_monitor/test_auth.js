const { createClient } = require('@supabase/supabase-js');

async function testAuth() {
  // Create Supabase client
  const supabase = createClient(
    'https://mkrczzgjeduruwxpanbj.supabase.co',
    'sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3'
  );

  try {
    console.log('Attempting to sign in...');
    const { data, error } = await supabase.auth.signInWithPassword({
      email: 'daming.lu@starmates.ai',
      password: 'test.1234!'
    });

    if (error) {
      console.error('Sign in error:', error);
      return;
    }

    console.log('Sign in successful!');
    console.log('User:', data.user.email);
    console.log('Access token preview:', data.session.access_token.substring(0, 50) + '...');

    // Test the token against the backend
    const response = await fetch('https://api.starmates.ai/api/v1/app/workflows?active_only=false&limit=10', {
      headers: {
        'Authorization': `Bearer ${data.session.access_token}`,
        'Content-Type': 'application/json'
      }
    });

    console.log('Backend API Response:', response.status, response.statusText);

    if (response.ok) {
      const workflows = await response.json();
      console.log('Got workflows:', workflows.length || 'N/A', 'workflows');
    } else {
      const errorText = await response.text();
      console.log('Error response:', errorText);
    }

  } catch (error) {
    console.error('Test failed:', error);
  }
}

testAuth();
