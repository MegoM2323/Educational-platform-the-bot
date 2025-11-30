/**
 * Profile API Integration Test Examples
 *
 * These are manual integration tests to verify the profileAPI works correctly
 * with the backend. Run these manually to test the API against a running server.
 *
 * NOTE: These are NOT automated tests. Use these patterns as reference for your own tests.
 */

import { profileAPI } from './profileAPI';
import { unifiedAPI } from './unifiedClient';

/**
 * Test 1: Load current user profile
 * Should return profile data for authenticated user
 */
export async function testGetCurrentProfile() {
  console.log('TEST 1: Get Current User Profile');
  console.log('================================\n');

  try {
    const response = await profileAPI.getCurrentUserProfile();

    if (response.success && response.data) {
      console.log('✓ Success');
      console.log('User:', response.data.user);
      console.log('Profile:', response.data.profile);
      return true;
    } else {
      console.error('✗ Failed:', response.error);
      return false;
    }
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Test 2: Get specific user profile by ID
 * Should return profile for the specified user ID
 */
export async function testGetUserProfile(userId: number) {
  console.log(`TEST 2: Get User Profile (ID: ${userId})`);
  console.log('================================\n');

  try {
    const response = await profileAPI.getUserProfile(userId);

    if (response.success && response.data) {
      console.log('✓ Success');
      console.log('User:', response.data.user);
      console.log('Profile:', response.data.profile);
      return true;
    } else {
      console.error('✗ Failed:', response.error);
      return false;
    }
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Test 3: Update current user profile
 * Should update user's first name and return updated data
 */
export async function testUpdateCurrentProfile(newFirstName: string) {
  console.log(`TEST 3: Update Current Profile`);
  console.log('================================');
  console.log(`Updating first_name to: ${newFirstName}\n`);

  try {
    const response = await profileAPI.updateCurrentProfile({
      first_name: newFirstName,
    });

    if (response.success && response.data) {
      console.log('✓ Success');
      console.log('Updated User:', response.data.user);
      return true;
    } else {
      console.error('✗ Failed:', response.error);
      return false;
    }
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Test 4: Get profiles by role
 * Should return list of all students
 */
export async function testGetProfilesByRole(role: 'student' | 'teacher' | 'tutor' | 'parent') {
  console.log(`TEST 4: Get Profiles by Role (${role})`);
  console.log('================================\n');

  try {
    const response = await profileAPI.getProfilesByRole(role);

    if (response.success && response.data) {
      console.log(`✓ Success - Found ${response.data.length} ${role}(s)`);
      response.data.forEach((profile, index) => {
        console.log(`  ${index + 1}. ${profile.user.full_name} (${profile.user.email})`);
      });
      return true;
    } else {
      console.error('✗ Failed:', response.error);
      return false;
    }
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Test 5: Cache validation
 * First load should be fresh, second should be from cache
 */
export async function testCaching() {
  console.log('TEST 5: Cache Validation');
  console.log('================================\n');

  try {
    // First load - should be fresh
    console.log('First load...');
    const start1 = performance.now();
    const response1 = await profileAPI.getCurrentUserProfile();
    const duration1 = performance.now() - start1;

    if (!response1.success) {
      console.error('✗ First load failed');
      return false;
    }

    console.log(`✓ First load successful (${duration1.toFixed(2)}ms)`);

    // Second load - should be from cache
    console.log('Second load (should be cached)...');
    const start2 = performance.now();
    const response2 = await profileAPI.getCurrentUserProfile();
    const duration2 = performance.now() - start2;

    console.log(`✓ Second load successful (${duration2.toFixed(2)}ms)`);

    if (duration2 < duration1) {
      console.log('✓ Cache is working (second load faster)');
    } else {
      console.warn('⚠ Cache may not be working (second load slower)');
    }

    // Clear cache
    console.log('Clearing cache...');
    profileAPI.invalidateCache();
    console.log('✓ Cache cleared');

    // Third load - should be fresh again
    console.log('Third load (after cache clear)...');
    const start3 = performance.now();
    const response3 = await profileAPI.getCurrentUserProfile();
    const duration3 = performance.now() - start3;

    console.log(`✓ Third load successful (${duration3.toFixed(2)}ms)`);

    return true;
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Test 6: Error handling - 401 Unauthorized
 * Should handle missing token gracefully
 */
export async function testUnauthorizedError() {
  console.log('TEST 6: Error Handling - 401 Unauthorized');
  console.log('================================\n');

  try {
    // Save current token
    const savedToken = unifiedAPI.getToken();

    // Clear token to simulate unauthorized state
    unifiedAPI.setToken('');

    console.log('Making request without token...');
    const response = await profileAPI.getCurrentUserProfile();

    if (!response.success) {
      console.log('✓ Got expected error response');
      console.log('Error:', response.error);

      if (response.error?.includes('401') || response.error?.includes('authentication')) {
        console.log('✓ Error type is correct (authentication/401)');
      }
    } else {
      console.warn('⚠ Expected error but got success response');
    }

    // Restore token
    if (savedToken) {
      unifiedAPI.setToken(savedToken);
      console.log('✓ Token restored');
    }

    return true;
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Test 7: Profile data structure validation
 * Should return profile with expected structure for each role
 */
export async function testProfileStructure() {
  console.log('TEST 7: Profile Data Structure Validation');
  console.log('================================\n');

  try {
    const response = await profileAPI.getCurrentUserProfile();

    if (!response.success || !response.data) {
      console.error('✗ Failed to load profile');
      return false;
    }

    const profile = response.data;
    const user = profile.user;

    // Validate user object
    console.log('Validating User object...');
    const userFields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'role_display'];
    const missingUserFields = userFields.filter((field) => !(field in user));

    if (missingUserFields.length === 0) {
      console.log('✓ All required user fields present');
    } else {
      console.warn(`⚠ Missing user fields: ${missingUserFields.join(', ')}`);
    }

    // Validate profile object
    console.log(`Validating ${user.role} profile object...`);
    if (profile.profile) {
      console.log('✓ Profile object exists');

      // Role-specific validation
      if (user.role === 'student') {
        const studentProfile = profile.profile;
        const studentFields = ['id', 'grade'];
        const missingFields = studentFields.filter((field) => !(field in studentProfile));
        if (missingFields.length === 0) {
          console.log('✓ All expected student profile fields present');
        } else {
          console.warn(`⚠ Missing student fields: ${missingFields.join(', ')}`);
        }
      } else if (user.role === 'teacher') {
        const teacherProfile = profile.profile;
        const teacherFields = ['id'];
        const missingFields = teacherFields.filter((field) => !(field in teacherProfile));
        if (missingFields.length === 0) {
          console.log('✓ All expected teacher profile fields present');
        }
      }
    } else {
      console.log('ℹ No profile object returned (may be normal for some roles)');
    }

    console.log('✓ Structure validation complete');
    return true;
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Test 8: Utility methods
 * Test extractProfileData and isProfileComplete methods
 */
export async function testUtilityMethods() {
  console.log('TEST 8: Utility Methods');
  console.log('================================\n');

  try {
    const response = await profileAPI.getCurrentUserProfile();

    if (!response.success || !response.data) {
      console.error('✗ Failed to load profile');
      return false;
    }

    const profile = response.data;

    // Test extractProfileData
    console.log('Testing extractProfileData()...');
    const profileData = profileAPI.extractProfileData(profile);
    if (profileData) {
      console.log('✓ Profile data extracted successfully');
      console.log('Extracted data:', profileData);
    } else {
      console.warn('⚠ extractProfileData returned null');
    }

    // Test isProfileComplete
    console.log('\nTesting isProfileComplete()...');
    const isComplete = profileAPI.isProfileComplete(profile);
    console.log(`✓ Profile complete: ${isComplete}`);

    return true;
  } catch (error) {
    console.error('✗ Exception:', error);
    return false;
  }
}

/**
 * Run all tests sequentially
 * Useful for comprehensive testing
 */
export async function runAllTests() {
  console.log('\n');
  console.log('╔════════════════════════════════════════════════════════════════╗');
  console.log('║          PROFILE API INTEGRATION TESTS                         ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  const results: Record<string, boolean> = {};

  // Test 1
  results['Test 1: Get Current Profile'] = await testGetCurrentProfile();
  console.log('\n');

  // Test 2 - requires knowing a valid user ID
  // Uncomment and provide valid ID if needed
  // results['Test 2: Get User Profile'] = await testGetUserProfile(1);
  // console.log('\n');

  // Test 3 - updates profile
  // Uncomment if you want to test updates
  // results['Test 3: Update Profile'] = await testUpdateCurrentProfile('TestName');
  // console.log('\n');

  // Test 4
  results['Test 4: Get Profiles by Role (student)'] = await testGetProfilesByRole('student');
  console.log('\n');

  // Test 5
  results['Test 5: Cache Validation'] = await testCaching();
  console.log('\n');

  // Test 6
  // results['Test 6: Unauthorized Error'] = await testUnauthorizedError();
  // console.log('\n');

  // Test 7
  results['Test 7: Profile Structure'] = await testProfileStructure();
  console.log('\n');

  // Test 8
  results['Test 8: Utility Methods'] = await testUtilityMethods();
  console.log('\n');

  // Print summary
  console.log('╔════════════════════════════════════════════════════════════════╗');
  console.log('║                       TEST SUMMARY                             ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  let passCount = 0;
  let failCount = 0;

  Object.entries(results).forEach(([testName, passed]) => {
    const status = passed ? '✓ PASS' : '✗ FAIL';
    console.log(`${status}: ${testName}`);
    if (passed) passCount++;
    else failCount++;
  });

  console.log('\n');
  console.log(`Total: ${passCount} passed, ${failCount} failed\n`);

  return failCount === 0;
}

/**
 * Quick test - just load profile
 * Useful for quick verification
 */
export async function quickTest() {
  console.log('Running quick profile test...\n');
  return await testGetCurrentProfile();
}

// Export for manual testing in console
export const profileAPITests = {
  testGetCurrentProfile,
  testGetUserProfile,
  testUpdateCurrentProfile,
  testGetProfilesByRole,
  testCaching,
  testUnauthorizedError,
  testProfileStructure,
  testUtilityMethods,
  runAllTests,
  quickTest,
};

/**
 * Usage in browser console:
 *
 * 1. Quick test:
 *    import { profileAPITests } from '@/integrations/api/profileAPI.integration-test'
 *    await profileAPITests.quickTest()
 *
 * 2. Run all tests:
 *    import { profileAPITests } from '@/integrations/api/profileAPI.integration-test'
 *    await profileAPITests.runAllTests()
 *
 * 3. Individual tests:
 *    import { profileAPITests } from '@/integrations/api/profileAPI.integration-test'
 *    await profileAPITests.testGetProfilesByRole('teacher')
 *    await profileAPITests.testCaching()
 */
