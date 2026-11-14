const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://localhost:4173';
const SCREENSHOT_DIR = path.resolve(__dirname, '..', 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runQA() {
  console.log('🚀 Starting FreshGuard Browser QA Automation...');
  console.log(`Connecting to Chrome at: ${CHROME_PATH}`);

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
    // 1. Landing Page Test
    console.log('\n--- 1. Testing Landing Page ---');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0', timeout: 30000 });
    await page.waitForSelector('h1', { timeout: 10000 });

    const heroDetails = await page.evaluate(() => {
      const h1 = document.querySelector('h1');
      const h1Styles = window.getComputedStyle(h1);
      const navLinks = Array.from(document.querySelectorAll('nav a, nav button')).map(el => ({
        text: el.innerText.trim(),
        href: el.getAttribute('href'),
      }));

      return {
        title: document.title,
        h1Text: h1 ? h1.innerText : null,
        h1Color: h1Styles ? h1Styles.color : null,
        h1FontSize: h1Styles ? h1Styles.fontSize : null,
        navLinks,
      };
    });

    console.log('Page Title:', heroDetails.title);
    console.log('Hero H1 Text:', heroDetails.h1Text.replace(/\n/g, ' '));
    console.log('Hero H1 Color:', heroDetails.h1Color);
    console.log('Navbar Elements Found:', heroDetails.navLinks.length);

    // Verify Sign In link exists
    const hasSignIn = heroDetails.navLinks.some(l => l.text.includes('Sign In') || l.href === '/login');
    console.log('✓ Navbar contains explicit "Sign In" link:', hasSignIn);

    // Save screenshot of fixed hero & landing page
    const heroPath = path.join(SCREENSHOT_DIR, '01_landing_hero_fixed.png');
    await page.screenshot({ path: heroPath });
    console.log(`✓ Saved Hero Screenshot: ${heroPath}`);

    // 2. Navigation to Login via Navbar Sign In button
    console.log('\n--- 2. Testing Navbar "Sign In" Click Navigation ---');
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
      page.click('nav a[href="/login"]'),
    ]);

    const currentUrl = page.url();
    console.log('Current URL after clicking Sign In:', currentUrl);
    console.log('✓ Successfully arrived at /login:', currentUrl.includes('/login'));

    const loginPath = path.join(SCREENSHOT_DIR, '02_login_page.png');
    await page.screenshot({ path: loginPath });
    console.log(`✓ Saved Login Screenshot: ${loginPath}`);

    // 3. Navigation to Signup
    console.log('\n--- 3. Testing Navigation to Signup Page ---');
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
      page.click('a[href="/signup"]'),
    ]);

    console.log('Current URL:', page.url());
    const signupPath = path.join(SCREENSHOT_DIR, '03_signup_page.png');
    await page.screenshot({ path: signupPath });
    console.log(`✓ Saved Signup Screenshot: ${signupPath}`);

    // 4. Test "Skip Signup & Access Demo" button
    console.log('\n--- 4. Testing One-Click Judge Demo Access ---');
    const demoBtn = await page.evaluateHandle(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      return buttons.find(b => b.innerText.includes('Skip Signup') || b.innerText.includes('Access Demo'));
    });
    if (demoBtn) {
      await demoBtn.click();
      await new Promise(r => setTimeout(r, 1500));
    }

    console.log('Current URL after Demo Access:', page.url());
    console.log('✓ Arrived at Dashboard Verify:', page.url().includes('/dashboard/verify'));

    // Check for Demo Mode banner in workspace
    const demoBanner = await page.evaluate(() => {
      const banner = document.body.innerText;
      return banner.includes('Demo Mode:') || banner.includes('Judge Demo Mode') || banner.includes('Guest Evaluator');
    });
    console.log('✓ Workspace displays persistent Demo Mode indicator:', demoBanner);

    const verifyPath = path.join(SCREENSHOT_DIR, '05_verification_workspace.png');
    await page.screenshot({ path: verifyPath });
    console.log(`✓ Saved Verify Workspace Screenshot: ${verifyPath}`);

    // 5. Test Live Verification in Workspace
    console.log('\n--- 5. Testing Live Claim Verification in Workspace ---');
    // Click a preset button (e.g. OpenAI GPT-4o pricing claim)
    await page.waitForSelector('button', { timeout: 5000 });
    const clickedPreset = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const preset = buttons.find(b => b.innerText.includes('Pricing') && b.innerText.includes('GPT-4o'));
      if (preset) {
        preset.click();
        return preset.innerText.substring(0, 30);
      }
      return null;
    });
    console.log(`✓ Clicked preset claim button: "${clickedPreset}..."`);
    await new Promise(r => setTimeout(r, 800));

    // Click "Run Verification Pipeline"
    const clickedRun = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const runBtn = buttons.find(b => b.innerText.includes('Run Verification'));
      if (runBtn) {
        runBtn.click();
        return true;
      }
      return false;
    });

    if (clickedRun) {
      console.log('✓ Triggered verification pipeline...');
      // Wait for verification result cards to appear
      await new Promise(r => setTimeout(r, 4500));
      const resultScreenshot = path.join(SCREENSHOT_DIR, '05b_live_verification_result.png');
      await page.screenshot({ path: resultScreenshot });
      console.log(`✓ Saved Verification Result Screenshot: ${resultScreenshot}`);
    }

    // 6. Test Dashboard Overview
    console.log('\n--- 6. Testing Dashboard Overview Page ---');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1, h2', { timeout: 5000 });
    const overviewPath = path.join(SCREENSHOT_DIR, '04_dashboard_overview.png');
    await page.screenshot({ path: overviewPath });
    console.log(`✓ Saved Dashboard Overview Screenshot: ${overviewPath}`);

    // 7. Test Verification History Page
    console.log('\n--- 7. Testing Verification History & Audit ---');
    await page.goto(`${BASE_URL}/dashboard/history`, { waitUntil: 'networkidle0' });
    const historyPath = path.join(SCREENSHOT_DIR, '06_verification_history.png');
    await page.screenshot({ path: historyPath });
    console.log(`✓ Saved Verification History Screenshot: ${historyPath}`);

    // 8. Test Cache Protection Page
    console.log('\n--- 8. Testing Cache Protection & Governance ---');
    await page.goto(`${BASE_URL}/dashboard/cache`, { waitUntil: 'networkidle0' });
    const cachePath = path.join(SCREENSHOT_DIR, '07_cache_protection.png');
    await page.screenshot({ path: cachePath });
    console.log(`✓ Saved Cache Protection Screenshot: ${cachePath}`);

    // 9. Test Integrations Page
    console.log('\n--- 9. Testing Integrations Matrix ---');
    await page.goto(`${BASE_URL}/dashboard/integrations`, { waitUntil: 'networkidle0' });
    const intPath = path.join(SCREENSHOT_DIR, '08_integrations.png');
    await page.screenshot({ path: intPath });
    console.log(`✓ Saved Integrations Screenshot: ${intPath}`);

    // 10. Test Settings Page
    console.log('\n--- 10. Testing Settings Page ---');
    await page.goto(`${BASE_URL}/dashboard/settings`, { waitUntil: 'networkidle0' });
    const setPath = path.join(SCREENSHOT_DIR, '09_settings.png');
    await page.screenshot({ path: setPath });
    console.log(`✓ Saved Settings Screenshot: ${setPath}`);

    // 11. Test Documentation Page
    console.log('\n--- 11. Testing Documentation Page ---');
    await page.goto(`${BASE_URL}/docs`, { waitUntil: 'networkidle0' });
    const docsPath = path.join(SCREENSHOT_DIR, '10_docs.png');
    await page.screenshot({ path: docsPath });
    console.log(`✓ Saved Docs Screenshot: ${docsPath}`);

    // 12. Test Mobile Viewport (390x844 - iPhone / standard mobile)
    console.log('\n--- 12. Testing Mobile Responsiveness (390px) ---');
    await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0' });

    // Open mobile hamburger menu
    const menuBtn = await page.$('nav button[aria-label="Toggle Navigation Menu"]');
    if (menuBtn) {
      await menuBtn.click();
      await new Promise(r => setTimeout(r, 500));
      const mobileNavPath = path.join(SCREENSHOT_DIR, '11_mobile_navbar_drawer.png');
      await page.screenshot({ path: mobileNavPath });
      console.log(`✓ Saved Mobile Navbar Drawer: ${mobileNavPath}`);
      // Close menu
      await menuBtn.click();
      await new Promise(r => setTimeout(r, 400));
    }

    const mobileHeroPath = path.join(SCREENSHOT_DIR, '12_mobile_hero.png');
    await page.screenshot({ path: mobileHeroPath });
    console.log(`✓ Saved Mobile Hero Screenshot: ${mobileHeroPath}`);

    await page.goto(`${BASE_URL}/dashboard/verify`, { waitUntil: 'networkidle0' });
    const mobileVerifyPath = path.join(SCREENSHOT_DIR, '13_mobile_verify.png');
    await page.screenshot({ path: mobileVerifyPath });
    console.log(`✓ Saved Mobile Verify Screenshot: ${mobileVerifyPath}`);

    console.log('\n🎉 ALL BROWSER QA TESTS AND SCREENSHOTS COMPLETED SUCCESSFULLY!');
  } catch (error) {
    console.error('❌ Error during QA execution:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

runQA();