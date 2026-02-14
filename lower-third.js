/**
 * JTF News - Lower Third Display
 * Loops through today's verified stories continuously
 * Each story displays with its cached audio, then moves to next
 *
 * Stories are evenly spread across each scrape cycle and randomized
 * to provide varied viewing experience.
 */

const FADE_TIME = 1000;       // Fade in/out duration (1 second)
const MIN_GAP_TIME = 10000;   // Minimum gap between stories (10 seconds)
const MAX_GAP_TIME = 120000;  // Maximum gap between stories (2 minutes)
const POLL_INTERVAL = 5000;   // Check for new stories every 5 seconds
const SCRAPE_CYCLE_MS = 300000; // 5 minute scrape cycle (matches config)
const STORIES_URL = '../data/stories.json';

let stories = [];
let shuffledQueue = [];       // Current cycle's shuffled story order
let lastPlayedFact = null;    // Track last played story to avoid back-to-back
let lastPlayedTimes = {};     // Track when each story was last played (fact -> timestamp)
let lastStoryEndTime = Date.now(); // Track when silence began (for max silence duration)
let isDisplaying = false;
let storyCountSinceSponsor = 0; // Counter for sponsor message frequency
let currentMessageIndex = 0;    // Which sponsor message to show next (alternates)

// Sponsor configuration (loaded from config.json, defaults here)
const SPONSOR_CONFIG = {
    enabled: true,
    frequency: 10,
    holdTime: 5000,  // 5 seconds display time
    messages: [
        {
            message: "JTF News is supported by viewers like you.",
            sourceText: "Support · github.com/sponsors/larryseyer"
        },
        {
            message: "Run JTF News as your screen saver.",
            sourceText: "Free · jtfnews.com/screensaver"
        }
    ]
};
let audioElement = null;
let cycleStartTime = 0;       // When current cycle started
let isFirstLoad = true;       // Track if this is initial page load

const MIN_REPLAY_INTERVAL = 30 * 60 * 1000; // 30 minutes minimum between replays
const MAX_SILENCE_DURATION = 15 * 60 * 1000; // 15 minutes max silence before forcing replay

// Freshness thresholds for frequency weighting
const FRESH_THRESHOLD = 6 * 60 * 60 * 1000;   // < 6 hours = fresh (3x weight)
const MEDIUM_THRESHOLD = 12 * 60 * 60 * 1000; // 6-12 hours = medium (2x weight)
// > 12 hours = stale (1x weight)

/**
 * Calculate how long ago a story was verified
 * Returns human-readable string like "2 hours ago" or "Earlier today"
 */
function getTimeAgo(timestamp) {
    if (!timestamp) return '';

    const now = Date.now();
    const storyTime = new Date(timestamp).getTime();
    const diffMs = now - storyTime;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffMinutes < 5) {
        return 'Just now';
    } else if (diffMinutes < 60) {
        return `${diffMinutes} min ago`;
    } else if (diffHours === 1) {
        return '1 hour ago';
    } else if (diffHours < 12) {
        return `${diffHours} hours ago`;
    } else {
        return 'Earlier today';
    }
}

/**
 * Get story age in milliseconds for freshness calculations
 */
function getStoryAge(story) {
    if (!story.timestamp) return Infinity;
    return Date.now() - new Date(story.timestamp).getTime();
}

/**
 * Get freshness weight for a story (higher = more likely to play)
 * Fresh (< 6 hrs): 3x, Medium (6-12 hrs): 2x, Stale (> 12 hrs): 1x
 */
function getFreshnessWeight(story) {
    const age = getStoryAge(story);
    if (age < FRESH_THRESHOLD) return 3;
    if (age < MEDIUM_THRESHOLD) return 2;
    return 1;
}

/**
 * Shuffle an array using Fisher-Yates algorithm with a fresh seed
 */
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

/**
 * Create a new queue for the cycle
 * Stories are fully shuffled (random order), then selected via weighted random
 * Freshness weighting happens at selection time, not queue ordering
 */
function reshuffleForNewCycle() {
    if (stories.length === 0) {
        shuffledQueue = [];
        return;
    }

    // Generate a fresh seed indicator for logging
    const seedIndicator = Math.random().toString(36).substring(2, 8);
    console.log(`Generating new queue with seed indicator: ${seedIndicator}`);

    // True random shuffle of ALL stories (no freshness sorting)
    // Freshness weighting is applied at selection time via getNextEligibleStory()
    shuffledQueue = shuffleArray([...stories]);

    // If the first story in new queue matches last played, move it to end
    if (lastPlayedFact && shuffledQueue.length > 1 && shuffledQueue[0].fact === lastPlayedFact) {
        shuffledQueue.push(shuffledQueue.shift());
        console.log('Moved last-played story to end to avoid back-to-back');
    }

    cycleStartTime = Date.now();

    // Count freshness tiers for logging
    const fresh = shuffledQueue.filter(s => getStoryAge(s) < FRESH_THRESHOLD).length;
    const medium = shuffledQueue.filter(s => getStoryAge(s) >= FRESH_THRESHOLD && getStoryAge(s) < MEDIUM_THRESHOLD).length;
    const stale = shuffledQueue.filter(s => getStoryAge(s) >= MEDIUM_THRESHOLD).length;
    console.log(`New cycle: ${fresh} fresh, ${medium} medium, ${stale} stale stories (randomly ordered)`);
}

/**
 * Calculate dynamic gap time based on number of stories
 * Evenly spreads stories across the scrape cycle
 */
function calculateDynamicGap() {
    if (shuffledQueue.length <= 1) {
        return MAX_GAP_TIME;
    }

    // Calculate time per story to fill the cycle
    // Account for approximate display time per story (audio ~10-15s + fade)
    const estimatedDisplayTime = 15000; // Average story display time
    const availableGapTime = SCRAPE_CYCLE_MS - (shuffledQueue.length * estimatedDisplayTime);
    const gapTime = Math.floor(availableGapTime / shuffledQueue.length);

    // Clamp to min/max bounds
    return Math.max(MIN_GAP_TIME, Math.min(gapTime, MAX_GAP_TIME));
}

/**
 * Load stories from stories.json
 */
async function loadStories() {
    try {
        const response = await fetch(STORIES_URL + '?t=' + Date.now());
        if (!response.ok) return;

        const data = await response.json();
        if (data.stories && data.stories.length > 0) {
            const oldCount = stories.length;
            const newCount = data.stories.length;

            // Check if stories changed or this is first load
            if (newCount !== oldCount || isFirstLoad) {
                console.log(`Stories ${isFirstLoad ? 'loaded (first time)' : 'changed'}: ${oldCount} -> ${newCount}`);
                stories = data.stories;

                // Always reshuffle on first load, or if queue is nearly empty
                if (isFirstLoad || shuffledQueue.length <= 1) {
                    reshuffleForNewCycle();
                    isFirstLoad = false;
                }
            } else {
                stories = data.stories;
            }
        }
    } catch (error) {
        console.log('No stories yet or error loading:', error.message);
    }
}

/**
 * Play audio for a story
 */
function playAudio(audioPath) {
    return new Promise((resolve) => {
        if (!audioElement) {
            audioElement = document.getElementById('tts-audio');
        }

        const onEnded = () => {
            audioElement.removeEventListener('ended', onEnded);
            audioElement.removeEventListener('error', onError);
            resolve('ended');
        };

        const onError = () => {
            audioElement.removeEventListener('ended', onEnded);
            audioElement.removeEventListener('error', onError);
            console.log('Audio failed to load, using fallback timing');
            resolve('error');
        };

        audioElement.addEventListener('ended', onEnded);
        audioElement.addEventListener('error', onError);

        // Load and play the story's cached audio
        audioElement.src = audioPath + '?t=' + Date.now();
        audioElement.load();
        audioElement.play().catch(() => {
            resolve('error');
        });
    });
}

/**
 * Calculate fallback hold time based on text length
 */
function calculateHoldTime(text) {
    const baseTime = 5000;
    const extraTime = Math.floor(text.length / 20) * 500;
    return Math.min(baseTime + extraTime, 15000);
}

/**
 * Sleep helper
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Display a single story with fade and audio
 * Uses dynamic gap time based on story count
 */
async function displayStory(story) {
    if (isDisplaying) return;
    isDisplaying = true;

    const lowerThird = document.getElementById('lower-third');
    const sourceBar = document.getElementById('source-bar');
    const factText = document.getElementById('fact-text');

    // Set content with time ago (Option 2: Timestamp in lower third)
    const timeAgo = getTimeAgo(story.timestamp);
    const sourceWithTime = timeAgo
        ? `${story.source || 'JTF News'} · ${timeAgo}`
        : (story.source || 'JTF News');
    sourceBar.textContent = sourceWithTime;
    factText.textContent = story.fact;

    // Fade in
    lowerThird.classList.remove('hidden');
    lowerThird.classList.add('visible');

    // Play audio and wait for it to finish
    const audioResult = await playAudio(story.audio);

    if (audioResult === 'error') {
        // Audio failed, use text-based timing
        await sleep(calculateHoldTime(story.fact));
    } else {
        // Audio played, keep text visible 2 more seconds after audio ends
        await sleep(2500);
    }

    // Fade out
    lowerThird.classList.remove('visible');
    lowerThird.classList.add('hidden');

    // Track this as last played for back-to-back prevention
    lastPlayedFact = story.fact;

    // Track when this story was played (for 30-minute minimum)
    lastPlayedTimes[story.fact] = Date.now();

    // Reset silence timer (a story just ended)
    lastStoryEndTime = Date.now();
    console.log(`Played story, next eligible in 30 minutes: "${story.fact.substring(0, 40)}..."`);

    // Calculate dynamic gap based on current story count
    const dynamicGap = calculateDynamicGap();

    // Wait for fade + dynamic gap
    await sleep(FADE_TIME + dynamicGap);

    isDisplaying = false;
}

/**
 * Display sponsor message (PBS-style acknowledgment)
 * Silent, visual-only, uses same lower-third infrastructure
 * Alternates between sponsor and screensaver messages
 */
async function displaySponsorMessage() {
    if (isDisplaying) return;
    isDisplaying = true;

    const lowerThird = document.getElementById('lower-third');
    const sourceBar = document.getElementById('source-bar');
    const factText = document.getElementById('fact-text');

    // Get current message and advance to next for next time
    const msg = SPONSOR_CONFIG.messages[currentMessageIndex];
    currentMessageIndex = (currentMessageIndex + 1) % SPONSOR_CONFIG.messages.length;

    // Set sponsor content
    sourceBar.textContent = msg.sourceText;
    factText.textContent = msg.message;

    // Fade in
    lowerThird.classList.remove('hidden');
    lowerThird.classList.add('visible');

    // Hold for sponsor display time (no audio)
    await sleep(SPONSOR_CONFIG.holdTime);

    // Fade out
    lowerThird.classList.remove('visible');
    lowerThird.classList.add('hidden');

    // Wait for fade
    await sleep(FADE_TIME + MIN_GAP_TIME);

    console.log(`[Sponsor] Displayed: "${msg.message}"`);
    isDisplaying = false;
}

/**
 * Check if a story is eligible to play
 * Normal: 30+ minutes since last play
 * Emergency: 15+ minutes of silence allows early replay
 */
function isEligibleToPlay(story) {
    const lastPlayed = lastPlayedTimes[story.fact];
    if (!lastPlayed) return true; // Never played before

    const timeSincePlay = Date.now() - lastPlayed;
    const silenceDuration = Date.now() - lastStoryEndTime;

    // Normal case: 30-min replay interval
    if (timeSincePlay >= MIN_REPLAY_INTERVAL) return true;

    // Emergency case: silence has exceeded max duration
    if (silenceDuration >= MAX_SILENCE_DURATION) return true;

    return false;
}

/**
 * Get next eligible story using weighted random selection
 * Option 3: Frequency weighting - fresh stories are more likely to be selected
 * Fresh (< 6 hrs): 3x weight, Medium (6-12 hrs): 2x weight, Stale (> 12 hrs): 1x weight
 */
function getNextEligibleStory() {
    // Get all eligible stories with their weights
    const eligible = [];
    for (let i = 0; i < shuffledQueue.length; i++) {
        if (isEligibleToPlay(shuffledQueue[i])) {
            eligible.push({
                index: i,
                story: shuffledQueue[i],
                weight: getFreshnessWeight(shuffledQueue[i])
            });
        }
    }

    if (eligible.length === 0) {
        return null; // No eligible stories
    }

    // Weighted random selection
    const totalWeight = eligible.reduce((sum, e) => sum + e.weight, 0);
    let random = Math.random() * totalWeight;

    for (const entry of eligible) {
        random -= entry.weight;
        if (random <= 0) {
            // Remove and return this story
            const timeAgo = getTimeAgo(entry.story.timestamp);
            console.log(`Selected story (weight ${entry.weight}, ${timeAgo}): "${entry.story.fact.substring(0, 40)}..."`);
            return shuffledQueue.splice(entry.index, 1)[0];
        }
    }

    // Fallback to first eligible (shouldn't reach here)
    return shuffledQueue.splice(eligible[0].index, 1)[0];
}

/**
 * Main loop - cycles through stories continuously
 * Stories are shuffled at the start of each cycle and evenly spaced
 * New seed generated each cycle for varied playback order
 */
async function runLoop() {
    while (true) {
        // Wait if no stories yet
        if (stories.length === 0) {
            await sleep(2000);
            continue;
        }

        // Start a new cycle if queue is empty
        if (shuffledQueue.length === 0) {
            reshuffleForNewCycle();

            // Still no stories after reshuffle? Wait and retry
            if (shuffledQueue.length === 0) {
                await sleep(2000);
                continue;
            }
        }

        // Check if it's time for sponsor message
        if (SPONSOR_CONFIG.enabled && storyCountSinceSponsor >= SPONSOR_CONFIG.frequency) {
            await displaySponsorMessage();
            storyCountSinceSponsor = 0;
            continue;
        }

        // Get next eligible story (30+ minutes since last play)
        const story = getNextEligibleStory();

        if (!story) {
            // All stories played recently, wait before checking again
            console.log('All stories played within last 30 minutes, waiting...');
            await sleep(30000); // Wait 30 seconds before checking again
            continue;
        }

        // Display the story and increment sponsor counter
        await displayStory(story);
        storyCountSinceSponsor++;
    }
}

/**
 * Poll for new stories periodically
 */
function startPolling() {
    // Initial load
    loadStories();

    // Continue polling
    setInterval(loadStories, POLL_INTERVAL);
}

/**
 * Initialize
 */
function start() {
    // Generate unique session ID to verify page actually reloaded
    const sessionId = Math.random().toString(36).substring(2, 10);
    console.log(`JTF News Lower Third starting... [Session: ${sessionId}]`);
    console.log(`Page loaded at: ${new Date().toISOString()}`);

    // Start polling for stories
    startPolling();

    // Start the display loop
    runLoop();
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
} else {
    start();
}
