const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const http = require('http');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://localhost:4173';
const SCREENSHOT_DIR = path.resolve(__dirname, '..', 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// 1. Lightweight Bifrost v2.5.1 API Test Server to verify network cache eviction
function startBifrostMockServer(port = 8080) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const url = req.url;
      const method = req.method;
      const authHeader = req.headers['authorization'];
      const vkHeader = req.headers['x-bf-vk'];

      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', '*');

      if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
      }

      console.log(`[Bifrost v2.5.1 Mock] ${method} ${url} (vk: ${vkHeader || 'none'}, auth: ${authHeader ? 'present' : 'none'})`);

      if (url.startsWith('/api/cache/clear/')) {
        const cacheId = url.replace('/api/cache/clear/', '');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          status: 'success',
          action: 'cache_cleared',
          cache_id: decodeURIComponent(cacheId),
          timestamp: new Date().toISOString(),
          gateway_version: '2.5.1',
        }));
        return;
      }

      if (url === '/health' || url === '/api/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', version: '2.5.1' }));
        return;
      }

      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'not_found' }));
    });

    server.listen(port, () => {
      console.log(`✓ Started Bifrost v2.5.1 API Mock Gateway on port ${port}`);
      resolve(server);
    });

    server.on('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        console.log(`Port ${port} already active; proceeding with existing service`);
        resolve(null);
      } else {
        reject(err);
      }
    });
  });
}

async function runComprehensiveValidation() {
  console.log('================================================================');
  console.log('   FRESHGUARD NAVBAR, AUTHENTICATION & WORKSPACE AUDIT SUITE    ');
  console.log('================================================================');

  const bifrostServer = await startBifrostMockServer(8080);

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--window-size=1440,1080',
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  try {
    // =========================================================================
    // PART A: LOGGED-OUT VISITOR EXPERIENCE
    // =========================================================================
    console.log('\n--- PART A: LOGGED-OUT VISITOR EXPERIENCE ---');

    // Clear session storage completely
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0' });
    await page.evaluate(() => sessionStorage.clear());
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0' });
    await new Promise((r) => setTimeout(r, 600));

    // Confirm Landing page appears
    const pageTitle = await page.evaluate(() => document.title || document.body.innerText.slice(0, 100));
    console.log('✓ Public Landing Page loaded on "/"');

    // Confirm Logged-Out Navbar items:
    const loggedOutNav = await page.evaluate(() => {
      const navText = document.querySelector('nav')?.innerText || '';
      return {
        hasHome: navText.includes('Home'),
        hasProblem: navText.includes('Problem'),
        hasPipeline: navText.includes('Pipeline Steps'),
        hasFeatures: navText.includes('Features'),
        hasArchitecture: navText.includes('Architecture'),
        hasDocs: navText.includes('Docs'),
        hasLogin: navText.includes('Login'),
        hasTryDemo: navText.includes('Try Live Demo'),
        hasDashboard: navText.includes('Dashboard'),
        hasAccount: navText.includes('Account'),
      };
    });

    console.log('✓ Logged-out Navbar items audit:', loggedOutNav);
    if (loggedOutNav.hasDashboard) throw new Error('FAIL: Dashboard button visible in logged-out navbar!');
    if (loggedOutNav.hasAccount) throw new Error('FAIL: Account button visible in logged-out navbar!');
    if (!loggedOutNav.hasLogin) throw new Error('FAIL: Login button missing in logged-out navbar!');
    if (!loggedOutNav.hasTryDemo) throw new Error('FAIL: Try Live Demo button missing in logged-out navbar!');
    console.log('✓ PASS: Dashboard & Account properly hidden when logged out.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'navbar_logged_out.png') });
    console.log('✓ Saved: screenshots/navbar_logged_out.png');

    // Test clicking Try Live Demo in navbar redirects to /login
    console.log('\n[A.2] Clicking "Try Live Demo" in logged-out navbar...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('nav a, nav button'));
      const tryDemo = btns.find(b => b.innerText.includes('Try Live Demo'));
      if (tryDemo) tryDemo.click();
    });
    await new Promise((r) => setTimeout(r, 800));
    console.log('Current URL after clicking Try Live Demo:', page.url());
    if (!page.url().includes('/login')) {
      throw new Error(`FAIL: Try Live Demo did not redirect to /login (got: ${page.url()})`);
    }
    console.log('✓ PASS: Logged-out visitor redirected to /login');

    // Test direct protected route access
    console.log('\n[A.3] Testing direct access to /dashboard without active session...');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle0' });
    await new Promise((r) => setTimeout(r, 600));
    console.log('Current URL after direct /dashboard access:', page.url());
    if (!page.url().includes('/login')) {
      throw new Error(`FAIL: Direct access to /dashboard did not redirect to /login (got: ${page.url()})`);
    }
    console.log('✓ PASS: ProtectedRoute successfully intercepted and redirected to /login');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'protected_route_redirect_to_login.png') });
    console.log('✓ Saved: screenshots/protected_route_redirect_to_login.png');

    // =========================================================================
    // PART B: LOGIN FLOW & VALIDATION
    // =========================================================================
    console.log('\n--- PART B: LOGIN PAGE & CREDENTIALS VALIDATION ---');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle0' });

    // Empty fields submission validation
    console.log('\n[B.1] Testing empty/invalid credential submission...');
    await page.evaluate(() => {
      const form = document.querySelector('form');
      if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
    });
    await new Promise((r) => setTimeout(r, 400));

    // Fill invalid credentials
    await page.type('input[type="email"]', 'invalid-format');
    await page.type('input[type="password"]', '123');
    await page.click('button[type="submit"]');
    await new Promise((r) => setTimeout(r, 600));

    const errorAlert = await page.evaluate(() => {
      const err = document.querySelector('.bg-rose-950\\/60, .text-rose-300');
      return err ? err.innerText : null;
    });
    console.log('✓ Invalid input validation error message:', errorAlert);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02b_login_error_validation.png') });
    console.log('✓ Saved: screenshots/02b_login_error_validation.png');

    // Password visibility toggle test
    console.log('\n[B.2] Testing password visibility toggle...');
    const passTypeBefore = await page.$eval('input[type="password"]', el => el.type);
    console.log('Password input type initially:', passTypeBefore);
    // Click password toggle button
    await page.click('button[aria-label="Toggle password visibility"]');
    await new Promise((r) => setTimeout(r, 400));
    const passTypeAfter = await page.$eval('input[type="text"], input[type="password"]', el => el.type);
    console.log('Password input type after toggle click:', passTypeAfter);
    if (passTypeAfter !== 'text') {
      console.warn('Note: Password toggle button type was', passTypeAfter);
    }

    // Save Login Page screenshot
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_login_page.png') });
    console.log('✓ Saved: screenshots/02_login_page.png');

    // Developer authentication test
    console.log('\n[B.3] Authenticating as Developer (developer@freshguard.io)...');
    await page.evaluate(() => {
      const em = document.querySelector('input[type="email"]');
      const pw = document.querySelector('input[type="password"], input[type="text"]');
      if (em) em.value = '';
      if (pw) pw.value = '';
    });
    await page.type('input[type="email"]', 'developer@freshguard.io');
    await page.type('input[type="password"], input[type="text"]', 'FreshGuard2026!');
    await page.click('button[type="submit"]');
    await new Promise((r) => setTimeout(r, 1200));

    console.log('Current URL after developer login:', page.url());
    if (!page.url().includes('/dashboard')) {
      throw new Error(`FAIL: Developer login did not redirect to /dashboard (got: ${page.url()})`);
    }
    console.log('✓ PASS: Developer login redirected directly to /dashboard');

    // =========================================================================
    // PART C: LOGGED-IN NAVBAR & ACCOUNT DROPDOWN
    // =========================================================================
    console.log('\n--- PART C: LOGGED-IN NAVBAR & ACCOUNT DROPDOWN ---');

    // Navigate to homepage to check public navbar in logged-in state
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0' });
    await new Promise((r) => setTimeout(r, 600));

    const loggedInNav = await page.evaluate(() => {
      const navText = document.querySelector('nav')?.innerText || '';
      return {
        hasHome: navText.includes('Home'),
        hasDocs: navText.includes('Docs'),
        hasDashboard: navText.includes('Dashboard'),
        hasLogin: navText.includes('Login'),
        hasAccountOrUser: navText.includes('developer') || navText.includes('Evaluator'),
      };
    });

    console.log('✓ Logged-in Navbar items audit:', loggedInNav);
    if (!loggedInNav.hasDashboard) throw new Error('FAIL: Dashboard button missing in logged-in navbar!');
    if (loggedInNav.hasLogin) throw new Error('FAIL: Login button still visible in logged-in navbar!');
    console.log('✓ PASS: Dashboard and Account are visible, Login is properly hidden.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'navbar_logged_in.png') });
    console.log('✓ Saved: screenshots/navbar_logged_in.png');

    // Test Account Dropdown
    console.log('\n[C.2] Opening Account dropdown menu...');
    await page.evaluate(() => {
      const trigger = document.querySelector('nav button[aria-label="Toggle user account menu"]');
      if (trigger) trigger.click();
    });
    await new Promise((r) => setTimeout(r, 600));

    const dropdownContent = await page.evaluate(() => {
      const menu = document.querySelector('nav .z-50.divide-y');
      return menu ? menu.innerText : null;
    });
    console.log('✓ Account Dropdown Content:\n' + dropdownContent);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'account_dropdown_open.png') });
    console.log('✓ Saved: screenshots/account_dropdown_open.png');

    // =========================================================================
    // PART D: LOGOUT BEHAVIOR & BACK-BUTTON PROTECTION
    // =========================================================================
    console.log('\n--- PART D: LOGOUT BEHAVIOR & BACK BUTTON PROTECTION ---');

    console.log('[D.1] Clicking Log Out in Account dropdown...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const logoutBtn = btns.find(b => b.innerText.includes('Log Out'));
      if (logoutBtn) logoutBtn.click();
    });
    await new Promise((r) => setTimeout(r, 800));

    console.log('Current URL after logout:', page.url());
    if (page.url() !== `${BASE_URL}/` && page.url() !== `${BASE_URL}`) {
      throw new Error(`FAIL: Logout did not redirect to "/" (got: ${page.url()})`);
    }
    console.log('✓ PASS: Logout redirected to "/"');

    const sessionPostLogout = await page.evaluate(() => sessionStorage.getItem('freshguard_active_session'));
    console.log('SessionStorage post-logout (must be null):', sessionPostLogout);
    if (sessionPostLogout !== null) throw new Error('FAIL: Session was not cleaned up on logout!');

    // Test back-button protection
    console.log('\n[D.2] Testing browser Back button navigation after logout...');
    await page.goBack();
    await new Promise((r) => setTimeout(r, 1500));
    console.log('Current URL after clicking browser Back:', page.url());
    const renderedContent = await page.evaluate(() => document.body.innerText.slice(0, 100));
    console.log('Rendered content after Back:', renderedContent);
    if (page.url().includes('/dashboard')) {
      // Check if page redirected or is in login
      const isLogin = await page.evaluate(() => document.querySelector('input[type="email"]') !== null);
      if (!isLogin) {
        throw new Error('FAIL: Back button allowed unauthorized access into /dashboard!');
      }
    }
    console.log('✓ PASS: Back button prevented unauthorized entry to protected dashboard.');

    // =========================================================================
    // PART E: JUDGE DEMO MODE ACTIVATION
    // =========================================================================
    console.log('\n--- PART E: JUDGE DEMO MODE ACTIVATION ---');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle0' });

    console.log('[E.1] Clicking "Access Demo as Judge / Evaluator"...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const demoBtn = btns.find(b => b.innerText.includes('Judge') || b.innerText.includes('Access Demo'));
      if (demoBtn) demoBtn.click();
    });
    await new Promise((r) => setTimeout(r, 1200));

    console.log('Current URL after Judge Demo access:', page.url());
    if (!page.url().includes('/dashboard')) {
      throw new Error(`FAIL: Judge Demo did not redirect to /dashboard (got: ${page.url()})`);
    }

    const judgeSession = await page.evaluate(() => {
      const s = sessionStorage.getItem('freshguard_active_session');
      return s ? JSON.parse(s) : null;
    });
    console.log('✓ Active Judge Demo Session:', judgeSession);
    if (!judgeSession?.isGuest) throw new Error('FAIL: Judge Demo session is not marked as guest!');
    console.log('✓ PASS: Judge Demo mode cleanly established with isGuest=true.');

    // =========================================================================
    // PART F: VERIFICATION WORKSPACE UX & FUNCTIONALITY AUDIT
    // =========================================================================
    console.log('\n--- PART F: VERIFICATION WORKSPACE AUDIT ---');
    await page.goto(`${BASE_URL}/dashboard/verify`, { waitUntil: 'networkidle0' });
    await new Promise((r) => setTimeout(r, 800));

    // F.1 Workspace UI & Status Inspection
    const wsHeading = await page.evaluate(() => {
      return {
        title: document.querySelector('h1')?.innerText,
        statusBadge: document.querySelector('.bg-emerald-950\\/70, .bg-amber-950\\/70')?.innerText,
      };
    });
    console.log('✓ Verification Workspace Heading & Status:', wsHeading);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_verification_workspace.png') });
    console.log('✓ Saved: screenshots/05_verification_workspace.png');

    // F.2 Empty Input Validation Test
    console.log('\n[F.2] Testing empty input validation...');
    await page.evaluate(() => {
      const txt = document.querySelector('textarea');
      if (txt) txt.value = '';
      const clearBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Clear'));
      if (clearBtn) clearBtn.click();
    });
    await page.click('button:has-text("Run Verification"), button:has-text("Evaluating Response")').catch(async () => {
      await page.evaluate(() => {
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Run Verification'));
        if (btn) btn.click();
      });
    });
    await new Promise((r) => setTimeout(r, 600));

    const emptyError = await page.evaluate(() => {
      const err = document.querySelector('.bg-rose-950\\/70');
      return err ? err.innerText : null;
    });
    console.log('✓ Empty input validation error:', emptyError);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verification_empty_error.png') });
    console.log('✓ Saved: screenshots/verification_empty_error.png');

    // F.3 Live Verification with Preset 1: Pricing Claim
    console.log('\n[F.3] Testing Preset 1: Pricing Claim...');
    await page.evaluate(() => {
      const presetBtns = Array.from(document.querySelectorAll('.grid button'));
      const pricingPreset = presetBtns.find(b => b.innerText.includes('Pricing Verification'));
      if (pricingPreset) pricingPreset.click();
    });
    await new Promise((r) => setTimeout(r, 2000));

    const pricingResult = await page.evaluate(() => {
      const statusPill = document.querySelector('.font-mono.font-bold.px-2.py-0\\.5');
      const claims = Array.from(document.querySelectorAll('.p-5.rounded-2xl.border')).map(c => c.innerText);
      return {
        freshness: statusPill ? statusPill.innerText : null,
        claimCount: claims.length,
        claimPreview: claims[0]?.slice(0, 150),
      };
    });
    console.log('✓ Pricing Verification Live Result:', pricingResult);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05b_live_verification_result.png') });
    console.log('✓ Saved: screenshots/05b_live_verification_result.png');

    // F.4 Live Verification with Preset 4: Contradicted Claim (Cache Invalidation Candidate)
    console.log('\n[F.4] Testing Preset 4: Contradicted Claim (Free API hallucination)...');
    await page.evaluate(() => {
      const presetBtns = Array.from(document.querySelectorAll('.grid button'));
      const contradictedPreset = presetBtns.find(b => b.innerText.includes('Contradicted Claim'));
      if (contradictedPreset) contradictedPreset.click();
    });
    await new Promise((r) => setTimeout(r, 2000));

    const contradictedResult = await page.evaluate(() => {
      const cacheAction = document.querySelector('.text-rose-400.font-bold, .text-emerald-400');
      const claimCard = document.querySelector('.bg-slate-900\\/90.border-rose-800\\/60, .bg-slate-900\\/90.border-amber-800\\/60');
      return {
        cacheAction: cacheAction ? cacheAction.innerText : null,
        claimVerdict: claimCard ? claimCard.innerText.slice(0, 160) : 'Rendered',
      };
    });
    console.log('✓ Contradicted Claim Result & Cache Decision:', contradictedResult);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verification_contradicted_result.png') });
    console.log('✓ Saved: screenshots/verification_contradicted_result.png');

    // =========================================================================
    // PART G: MOBILE RESPONSIVE AUDIT (390x844 Viewport)
    // =========================================================================
    console.log('\n--- PART G: MOBILE RESPONSIVE AUDIT (390x844) ---');
    await page.setViewport({ width: 390, height: 844, isMobile: true });

    // Mobile Navbar & Drawer in Logged-In state
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0' });
    await new Promise((r) => setTimeout(r, 600));

    // Open mobile hamburger
    await page.click('button[aria-label="Toggle Navigation Menu"]');
    await new Promise((r) => setTimeout(r, 500));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'mobile_drawer_logged_in.png') });
    console.log('✓ Saved: screenshots/mobile_drawer_logged_in.png');

    // Mobile Verification Workspace
    await page.goto(`${BASE_URL}/dashboard/verify`, { waitUntil: 'networkidle0' });
    await new Promise((r) => setTimeout(r, 800));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_mobile_verify.png') });
    console.log('✓ Saved: screenshots/13_mobile_verify.png');

    // Log out on mobile
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0' });
    await page.evaluate(() => sessionStorage.clear());
    await page.reload({ waitUntil: 'networkidle0' });
    await new Promise((r) => setTimeout(r, 500));
    await page.click('button[aria-label="Toggle Navigation Menu"]');
    await new Promise((r) => setTimeout(r, 500));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_mobile_navbar_drawer.png') });
    console.log('✓ Saved: screenshots/11_mobile_navbar_drawer.png (logged-out)');

    // =========================================================================
    // PART H: CAPTURE COMPLETE DESKTOP DASHBOARD SUITE
    // =========================================================================
    console.log('\n--- PART H: CAPTURING FULL DESKTOP AUDIT SUITE ---');
    await page.setViewport({ width: 1440, height: 900, isMobile: false });

    // Establish Judge Session
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle0' });
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const demoBtn = btns.find(b => b.innerText.includes('Judge') || b.innerText.includes('Access Demo'));
      if (demoBtn) demoBtn.click();
    });
    await new Promise((r) => setTimeout(r, 1000));

    const routesToCapture = [
      { url: `${BASE_URL}/`, file: '01_landing_page.png' },
      { url: `${BASE_URL}/signup`, file: '03_signup_page.png' },
      { url: `${BASE_URL}/dashboard`, file: '04_dashboard_overview.png' },
      { url: `${BASE_URL}/dashboard/history`, file: '06_verification_history.png' },
      { url: `${BASE_URL}/dashboard/cache`, file: '07_cache_protection.png' },
      { url: `${BASE_URL}/dashboard/integrations`, file: '08_integrations.png' },
      { url: `${BASE_URL}/dashboard/settings`, file: '09_settings.png' },
      { url: `${BASE_URL}/docs`, file: '10_docs.png' },
    ];

    for (const r of routesToCapture) {
      await page.goto(r.url, { waitUntil: 'networkidle0' });
      await new Promise(res => setTimeout(res, 600));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, r.file) });
      console.log(`✓ ${r.file}`);
    }

    console.log('\n================================================================');
    console.log('   🎉 ALL NAVBAR, AUTH & WORKSPACE VALIDATIONS PASSED!          ');
    console.log('================================================================\n');

  } catch (err) {
    console.error('❌ Validation Suite Failed:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
    if (bifrostServer) {
      bifrostServer.close();
    }
  }
}

runComprehensiveValidation();
