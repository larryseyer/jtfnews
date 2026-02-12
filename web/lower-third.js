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
let isDisplaying = false;
let audioElement = null;
let cycleStartTime = 0;       // When current cycle started

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
 * Create a new shuffled queue for the cycle
 * Ensures the last played story isn't first in the new queue
 */
function reshuffleForNewCycle() {
    if (stories.length === 0) {
        shuffledQueue = [];
        return;
    }

    // Shuffle with a new random seed (Math.random uses current time)
    shuffledQueue = shuffleArray(stories);

    // If the first story in new shuffle matches last played, move it to the end
    if (lastPlayedFact && shuffledQueue.length > 1 && shuffledQueue[0].fact === lastPlayedFact) {
        const first = shuffledQueue.shift();
        shuffledQueue.push(first);
        console.log('Moved last-played story to end of queue to avoid back-to-back');
    }

    cycleStartTime = Date.now();
    console.log(`New cycle started with ${shuffledQueue.length} stories shuffled`);
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

            // Check if stories changed
            if (newCount !== oldCount) {
                console.log(`Stories changed: ${oldCount} -> ${newCount}`);
                stories = data.stories;

                // If we have more stories and queue is empty or nearly done, reshuffle
                if (shuffledQueue.length <= 1) {
                    reshuffleForNewCycle();
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

    // Set content
    sourceBar.textContent = story.source || 'JTF News';
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

    // Calculate dynamic gap based on current story count
    const dynamicGap = calculateDynamicGap();

    // Wait for fade + dynamic gap
    await sleep(FADE_TIME + dynamicGap);

    isDisplaying = false;
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

        // Get next story from shuffled queue
        const story = shuffledQueue.shift();

        // Display the story
        await displayStory(story);
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
    console.log('JTF News Lower Third starting...');

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
