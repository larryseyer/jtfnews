/**
 * JTF News - Lower Third Display
 * Loops through today's verified stories continuously
 * Each story displays with its cached audio, then moves to next
 */

const FADE_TIME = 1000;       // Fade in/out duration (1 second)
const GAP_TIME = 45000;       // Gap between stories (45 seconds)
const POLL_INTERVAL = 5000;   // Check for new stories every 5 seconds
const MIN_REPEAT_GAP = 600000; // Minimum 10 minutes before repeating same story
const STORIES_URL = '../data/stories.json';

let stories = [];
let storyPlayTimes = new Map();  // Track when each story was last played (by fact text)
let isDisplaying = false;
let audioElement = null;

/**
 * Load stories from stories.json
 */
async function loadStories() {
    try {
        const response = await fetch(STORIES_URL + '?t=' + Date.now());
        if (!response.ok) return;

        const data = await response.json();
        if (data.stories && data.stories.length > 0) {
            // Check if we have new stories
            if (data.stories.length > stories.length) {
                console.log(`Loaded ${data.stories.length} stories (${data.stories.length - stories.length} new)`);
            }
            stories = data.stories;

            // Clean up play times for stories no longer in the list
            const currentFacts = new Set(stories.map(s => s.fact));
            for (const fact of storyPlayTimes.keys()) {
                if (!currentFacts.has(fact)) {
                    storyPlayTimes.delete(fact);
                }
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
        // Audio played, add small buffer
        await sleep(500);
    }

    // Fade out
    lowerThird.classList.remove('visible');
    lowerThird.classList.add('hidden');

    // Wait for fade + gap
    await sleep(FADE_TIME + GAP_TIME);

    isDisplaying = false;
}

/**
 * Get stories eligible for playback (not played within MIN_REPEAT_GAP)
 */
function getEligibleStories() {
    const now = Date.now();
    return stories.filter(story => {
        const lastPlayed = storyPlayTimes.get(story.fact) || 0;
        return (now - lastPlayed) >= MIN_REPEAT_GAP;
    });
}

/**
 * Main loop - cycles through stories continuously
 * Stories won't repeat until MIN_REPEAT_GAP (10 min) has passed
 * If all stories are on cooldown, waits until one becomes eligible
 */
async function runLoop() {
    while (true) {
        // Wait if no stories yet
        if (stories.length === 0) {
            await sleep(2000);
            continue;
        }

        // Find stories eligible for playback
        const eligible = getEligibleStories();

        if (eligible.length === 0) {
            // All stories on cooldown, wait and check again
            await sleep(5000);
            continue;
        }

        // Play the first eligible story
        const story = eligible[0];
        await displayStory(story);

        // Track when this story was played
        storyPlayTimes.set(story.fact, Date.now());
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
